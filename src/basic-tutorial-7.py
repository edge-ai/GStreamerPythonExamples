import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Pipelines with more than one sink usually need to be multithreaded, 
# because, to be synchronized, sinks usually block execution until all other sinks are ready, 
# and they cannot get ready if there is only one thread, being blocked by the first sink.

if __name__ == '__main__':
    pipeline = None

    # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.init
    print('initializing Gst...')
    Gst.init(None)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.make
    print('creating elements...')
    audio_source = Gst.ElementFactory.make("audiotestsrc", "audio_source")
    tee = Gst.ElementFactory.make("tee", "tee")
    audio_queue = Gst.ElementFactory.make("queue", "audio_queue")
    audio_convert = Gst.ElementFactory.make("audioconvert", "audio_convert")
    audio_resample = Gst.ElementFactory.make("audioresample", "audio_resample")
    audio_sink = Gst.ElementFactory.make("autoaudiosink", "audio_sink")
    video_queue = Gst.ElementFactory.make("queue", "video_queue")
    visual = Gst.ElementFactory.make("wavescope", "visual")
    video_convert = Gst.ElementFactory.make("videoconvert", "csp")
    video_sink = Gst.ElementFactory.make("autovideosink", "video_sink")

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pipeline.html#Gst.Pipeline.new
    print('creating an empty pipeline')
    pipeline = Gst.Pipeline.new("test-pipeline")

    if audio_source is None or tee is None or audio_queue is None or audio_convert is None or audio_resample is None or \
        video_queue is None or visual is None or video_convert is None or video_sink is None or pipeline is None:
        print('failed to create elements or a pipeline')
        sys.exit(1)

    # https://lazka.github.io/pgi-docs/#GObject-2.0/classes/Object.html#GObject.Object.set_property
    print('modifying the source properties...')
    audio_source.set_property('freq', 215.0)
    visual.set_property('shader', 0)
    visual.set_property('style', 1)

    # Link all elements that can be automatically linked because they have "Always" pads
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bin.html#Gst.Bin.add
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.link
    print('building the pipeline...')
    pipeline.add(audio_source)
    pipeline.add(tee)
    pipeline.add(audio_queue)
    pipeline.add(audio_convert)
    pipeline.add(audio_resample)
    pipeline.add(audio_sink)
    pipeline.add(video_queue)
    pipeline.add(visual)
    pipeline.add(video_convert)
    pipeline.add(video_sink)
    if not audio_source.link(tee) or not audio_queue.link(audio_convert) or not audio_convert.link(audio_resample) or not audio_resample.link(audio_sink) \
        or not video_queue.link(visual) or not visual.link(video_convert) or not video_convert.link(video_sink):
        print('failed to link')
        pipeline.set_state(Gst.State.NULL)
        sys.exit(1)
    
    # Manually link the Tee, which has "Request" pads
    print('linking elements...')
    tee_audio_pad = tee.get_request_pad("src_%u")
    queue_audio_pad = audio_queue.get_static_pad("sink")
    tee_video_pad = tee.get_request_pad("src_%u")
    queue_video_pad = video_queue.get_static_pad("sink")
    if not tee_audio_pad.link(queue_audio_pad) == Gst.PadLinkReturn.OK \
        or not tee_video_pad.link(queue_video_pad) == Gst.PadLinkReturn.OK:
        print('tee could not be linked')
        pipeline.set_state(Gst.State.NULL)
        sys.exit(1)

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
    if pipeline is not None:
        pipeline.set_state(Gst.State.NULL)

    print('finished running multithreading and pad availability example')