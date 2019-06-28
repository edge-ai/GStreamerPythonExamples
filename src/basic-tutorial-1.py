
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

def get_message_from_bus(gst_bus):
    return gst_bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ANY)

if __name__ == '__main__':
    gst_element = None
    gst_bus = None
    gst_message = None

    # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.init
    print('initializing Gst...')
    Gst.init(None)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.parse_launch
    print('building a pipeline...')
    gst_element = Gst.parse_launch("playbin uri=https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm")
    if gst_element == None:
        print('failed to build a pipeline')
        sys.exit(1)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.set_state
    print('start playing the pipeline...')
    gst_element.set_state(Gst.State.PLAYING)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_bus
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bus.html#Gst.Bus.timed_pop_filtered
    print('wait until error or EOS')
    gst_bus = gst_element.get_bus()
    gst_message = get_message_from_bus(gst_bus)
    if gst_message == None:
        print('failed to get a message')
    else:

        while gst_message.type != Gst.MessageType.EOS and gst_message.type != Gst.MessageType.ERROR:
            gst_message = gst_bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ANY)
            if gst_message is None:
                print('failed to get a message')
                break
            else:
                print('a message {} was found'.format(gst_message.type))


    # set state NULL
    print('disposing the pipeline...')
    gst_element.set_state(Gst.State.NULL)

    print('finished running hellow world example')