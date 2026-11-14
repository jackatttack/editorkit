"""Print every editor event for a minute, then stop."""
import time


import editorkit as ek

started = time.time()


def report(event, started=started, clock=time.time, ek=ek):
    if clock() - started > 60:
        ek.clear_listeners()
        print('editorkit: stopped watching')
        return
    if event['kind'] != 'text':
        print('%-9s %r -> %r' % (event['kind'], event['old'], event['new']))
    else:
        print('text      changed')


ek.on_change(report)
print('Watching for 60 s: type, switch tabs, show the console.')
