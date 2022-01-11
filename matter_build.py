import sublime
import sublime_plugin

import subprocess
import threading
import os
import re

FILE_REGEX = r"^INFO *(.*[^:]):(\d+):(\d+): (?:fatal )?((?:error|warning): .+)$"
MATCH_DEBUG = False

def per_line(text):
    while '\n' in text:
        idx = text.find('\n')
        yield text[:idx + 1]
        text = text[idx + 1:]

    if text:
       yield text

class MatterDockerBuild(sublime_plugin.WindowCommand):

    encoding = 'utf-8'
    killed = False
    proc = None
    panel = None
    panel_lock = threading.Lock()
    build_targets = None
    last_selected_index = -1

    def targets(self):
        if self.build_targets is None:
            self.build_targets = []
            for t in self.compute_build_targets():
                if ' (NOGLOB' in t:
                    idx = t.find(' (NOGLOB')
                    trigger, annotation = t[:idx], t[idx + 2:]
                    self.build_targets.append([trigger, annotation])
                else:
                    self.build_targets.append([t,])

        return self.build_targets

    def compute_build_targets(self):
        items = subprocess.check_output([
            'docker', 'exec', '-w', '/workspace', 'bld_vscode', '/bin/bash', '-c',
            'source ./scripts/activate.sh 2>&1 >/dev/null && ./scripts/build/build_examples.py --log-level fatal targets']).split(b'\n')

        for item in items:
            yield item.decode('utf8')


    def is_enabled(self, kill=False):
        # The Cancel build option should only be available
        # when the process is still running
        if kill:
            return self.proc is not None and self.proc.poll() is None
        return True

    def target_input_done(self, target_index):
        if target_index < 0:
            return

        self.last_selected_index = target_index
        target = self.targets()[target_index][0]

        self.run_build(target)


    def run(self, kill=False):
        if kill:
            if self.proc:
                self.killed = True
                self.proc.terminate()
            return

        with self.panel_lock:
            # Creating the panel implicitly clears any previous contents
            # self.panel = self.window.create_output_panel('matter_build')
            self.panel = self.window.create_output_panel('exec')

        self.window.show_quick_panel(
           self.targets(),
           self.target_input_done,
           selected_index=self.last_selected_index,
           placeholder='Target',
        )


    def run_build(self, target):
        vars = self.window.extract_variables()

        # A lock is used to ensure only one thread is
        # touching the output panel at a time
        with self.panel_lock:

            # Enable result navigation. The result_file_regex does
            # the primary matching, but result_line_regex is used
            # when build output includes some entries that only
            # contain line/column info beneath a previous line
            # listing the file info. The result_base_dir sets the
            # path to resolve relative file names against.
            settings = self.panel.settings()
            settings.set('result_file_regex', FILE_REGEX)
            settings.set('result_line_regex', "")

            # TODO: this should be dynamic by project directory or given via build
            # configuration.
            settings.set('result_base_dir', '/home/andrei/devel/connectedhomeip/out/fake')


            # do not attempt to interpret syntax
            self.panel.assign_syntax(
                sublime.Syntax('Packages/Text/Plain text.tmLanguage', 'Plain Text', False, 'text.plain'))

            self.window.run_command('show_panel', {'panel': 'output.exec'})

        if self.proc is not None:
            self.proc.terminate()
            self.proc = None


        self.queue_write("Starting build for %s\n" % target)

        args ="docker exec -w /workspace bld_vscode /bin/bash -c".split()

        # TODO: this would work if we would not be using the quickselect panel.
        #       We should have a 'GLOB' in  quickselect which provides a glob prompt
        if '*' in target or '{' in target or '?' in target:
            target_str = '--target-glob "%s"' % target
        else:
            target_str = '--target "%s"' % target

        args.append('source ./scripts/activate.sh && ./scripts/build/build_examples.py --no-log-timestamps %s build' % target_str)

        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.killed = False

        threading.Thread(
            target=self.read_handle,
            args=(self.proc.stdout,)
        ).start()

    def read_handle(self, handle):
        print("Matter docker build run loop starting")
        chunk_size = 2 ** 13
        out = b''
        while True:
            try:
                data = os.read(handle.fileno(), chunk_size)
                # If exactly the requested number of bytes was
                # read, there may be more data, and the current
                # data may contain part of a multibyte char
                out += data
                if len(data) == chunk_size:
                    continue
                if data == b'' and out == b'':
                    raise IOError('EOF')
                # We pass out to a function to ensure the
                # timeout gets the value of out right now,
                # rather than a future (mutated) version
                self.queue_write(out.decode(self.encoding))
                if data == b'':
                    raise IOError('EOF')
                out = b''
            except (UnicodeDecodeError) as e:
                msg = 'Error decoding output using %s - %s'
                self.queue_write(msg  % (self.encoding, str(e)))
                break
            except (IOError):
                if self.killed:
                    msg = 'Cancelled'
                else:
                    msg = 'Finished'
                self.queue_write('\n[%s]' % msg)
                break
        print("Matter docker build run loop completed")

        with self.panel_lock:
            regions = self.panel.find_all(FILE_REGEX)
            self.panel.add_regions("docker.build.errors", regions=regions, scope="region.redish")



    def queue_write(self, text):
        sublime.set_timeout(lambda: self.do_write(text), 1)

    def do_write(self, text):
        with self.panel_lock:
            self.panel.set_read_only(False)
            for t in per_line(text):
              self.panel.run_command('append', {'characters': t})

              if MATCH_DEBUG:
                m = re.compile(FILE_REGEX).match(t)
                if m:
                  print("  Detected build error: %r" % (m.groups(), ))
            self.panel.set_read_only(True)
            self.panel.run_command('move_to', {'to': 'eof', "extend": False})
