class Event(object):
    def __init__(self):
        self.handlers = set()

    def __iadd__(self, handler):
        self.handlers.add(handler)
        return self

    def __isub__(self, handler):
        try: self.handlers.remove(handler)
        except: raise ValueError("Unhandled event")
        return self

    def __call__(self, *args, **kargs):
        for handler in self.handlers:
            handler(*args, **kargs)

    def __len__(self):
        return len(self.handlers)

EVENT_HANDLERS = {}
def get_event_handler(namespace):
    global EVENT_HANDLERS
    if namespace not in EVENT_HANDLERS.keys():
        event = Event()
        EVENT_HANDLERS[namespace] = event
        return event
    return EVENT_HANDLERS[namespace]

def del_event_handler(namespace):
    global EVENT_HANDLERS
    if namespace not in EVENT_HANDLERS.keys():
        raise Exception('%s does not exist' % namespace)
    del EVENT_HANDLERS[namespace]
