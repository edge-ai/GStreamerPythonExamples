import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

if __name__ == '__main__':
    print('declaring variables of classes inherits from Gst.Object that should be unreferenced')
    pipeline = None
    gst_bus = None

    # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.init
    print('initializing Gst...')
    Gst.init(None)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.make
    print('creating elements...')
    source = Gst.ElementFactory.make("videotestsrc", "source")
    sink = Gst.ElementFactory.make("autovideosink", "sink")

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pipeline.html#Gst.Pipeline.new
    print('creating an empty pipeline')
    pipeline = Gst.Pipeline.new("test-pipeline")

    if source is None or sink is None or pipeline is None:
        print('failed to create elements or a pipeline')
        sys.exit(1)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bin.html#Gst.Bin.add
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.link
    print('building the pipeline...')
    pipeline.add(source)
    pipeline.add(sink)
    if not source.link(sink):
        print('failed to link')
        pipeline.set_state(Gst.State.NULL)
        sys.exit(1)

    # https://lazka.github.io/pgi-docs/#GObject-2.0/classes/Object.html#GObject.Object.set_property
    print('modifying the source properties...')
    source.set_property('pattern', 0)
    source.set_property('num-buffers', 30)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.set_state
    print('start playing the pipeline...')
    gst_state_change_return = pipeline.set_state(Gst.State.PLAYING)
    if gst_state_change_return == Gst.StateChangeReturn.FAILURE:
        print('failed to play')
        pipeline.set_state(Gst.State.NULL)
        sys.exit(1)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_bus
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bus.html#Gst.Bus.timed_pop_filtered
    print('wait until error or EOS')
    gst_bus = pipeline.get_bus()
    gst_message = gst_bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)

    if gst_message is not None:

        message_type = gst_message.type
        if message_type == Gst.MessageType.ERROR:
            gerror, debug = gst_message.parse_error()
            print('error {} happened at {}'.format(gerror.message, debug))
        elif message_type == Gst.MessageType.EOS:
            print('EOS reached')
        else:
            print('this should not happen, the received message type is unexpectedly {}'.format(message_type))

    # set state NULL
    # call unref(), but which will leave many CRITICAL error messages as follows...
    # (python3:772): GLib-GObject-CRITICAL **: 08:49:46.297: g_object_unref: assertion 'G_IS_OBJECT (object)' failed
    print('disposing the pipeline...')
    pipeline.set_state(Gst.State.NULL)

    print('finished running manual hellow world example')