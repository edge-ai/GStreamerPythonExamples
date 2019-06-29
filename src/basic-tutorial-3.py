import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

class CustomData():

    def __init__(self):
        self._pipeline = None
        self._source = None
        self._convert = None
        self._sink = None

        self._bus = None

    @property
    def convert(self):
        return self._convert    

    def create_pipeline(self):
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.make
        print('creating elements...')
        self._source = Gst.ElementFactory.make("uridecodebin", "source")
        self._convert = Gst.ElementFactory.make("audioconvert", "convert")
        self._sink = Gst.ElementFactory.make("autoaudiosink", "sink")

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pipeline.html#Gst.Pipeline.new
        print('creating an empty pipeline')
        self._pipeline = Gst.Pipeline.new("test-pipeline")

        if self._source is None or self._sink is None or self._convert is None or self._pipeline is None:
            print('failed to create elements or a pipeline')
            return False

        print('successfully created an empty pipeline')
        return True

    def build_pipeline(self):
        # Build the pipeline. Note that we are NOT linking the source at this point. We will do it later. 
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bin.html#Gst.Bin.add
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.link
        print('building the pipeline...')
        self._pipeline.add(self._source)
        self._pipeline.add(self._convert)
        self._pipeline.add(self._sink)
        if not self._convert.link(self._sink):
            print('failed to link from convert to sink')
            self._pipeline.unref()
            return False

        print('successfully build a pipeline')
        return True

    def setup_source(self):
        # https://lazka.github.io/pgi-docs/#GObject-2.0/classes/Object.html#GObject.Object.set_property
        print('modifying the source properties...')
        self._source.set_property('uri', 'https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm')
        # https://lazka.github.io/pgi-docs/#GObject-2.0/classes/Object.html#GObject.Object.connect
        print('connecting to the pad-added signal...')
        self._source.connect("pad-added", self.pad_added_handler)

    def pad_added_handler(self, src, new_pad):
        print('pad_added_handler was called back')

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_static_pad
        sink_pad = self.convert.get_static_pad('sink')

        print('received a new pad {} from {}'.format(new_pad, src))

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pad.html#Gst.Pad.is_linked
        if sink_pad.is_linked():
            print('sink pad is already linked. ignoring...')
            return

        print('checking the pad capabilities...')
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pad.html#Gst.Pad.get_current_caps
        new_pad_caps = new_pad.get_current_caps()
        if new_pad_caps is None:
            print('the pad has no caps')
            return
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Caps.html#Gst.Caps.get_structure
        new_pad_struct = new_pad_caps.get_structure(0)
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Structure.html#Gst.Structure.get_name
        new_pad_type = new_pad_struct.get_name()
        if not 'audio/x-raw' in new_pad_type:
            # if simply ignores the video pad, it will raise an error as follows.
            # error Internal data stream error. happened at /dvs/git/dirty/git-master_linux/3rdparty/gst/gst-omx/omx/gstomxvideodec.c(3000): 
            # gst_omx_video_dec_loop (): /GstPipeline:test-pipeline/GstURIDecodeBin:source/GstDecodeBin:decodebin0/GstOMXVP8Dec-omxvp8dec:omxvp8dec-omxvp8dec0: 
            # stream stopped, reason not-linked
            print('It has type {} which is not raw audio, ignoring...'.format(new_pad_type))
            return

        print('linking the new pad to the sink pad...')
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pad.html#Gst.Pad.link
        link_return = new_pad.link(sink_pad)
        if link_return != Gst.PadLinkReturn.OK:
            print('link failed')
        else:
            print('link succeeded')

    def play_pipeline(self):
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.set_state
        print('start playing the pipeline...')
        gst_state_change_return = self._pipeline.set_state(Gst.State.PLAYING)
        if gst_state_change_return == Gst.StateChangeReturn.FAILURE:
            print('failed to play')
            self.dispose()
            return False

        print('successfully played the pipeline')
        return True

    def listen_to_bus(self):
        terminated = False

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_bus
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bus.html#Gst.Bus.timed_pop_filtered
        print('listening to the bus...')
        self._bus = self._pipeline.get_bus()

        while not terminated:
            gst_message = self._bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS)

            if gst_message is not None:

                message_type = gst_message.type
                if message_type == Gst.MessageType.ERROR:
                    gerror, debug = gst_message.parse_error()
                    print('error {} happened at {}'.format(gerror.message, debug))
                    terminated = True
                elif message_type == Gst.MessageType.EOS:
                    print('EOS reached')
                    terminated = True
                elif message_type == Gst.MessageType.STATE_CHANGED:
                    # We are only interested in state-changed messages from the pipeline
                    print('received a state change message {} from {}'.format(message_type, gst_message.src))
                    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Message.html#Gst.Message.parse_state_changed
                    oldState, newState, pending = gst_message.parse_state_changed()
                    print('state changed from {} to {}'.format(oldState, newState))
                else:
                    print('this should not happen, the received message type is unexpectedly {}'.format(message_type))

    def dispose(self):
        # not call unref(), but which will leave many CRITICAL error messages as follows...
        # (python3:772): GLib-GObject-CRITICAL **: 08:49:46.297: g_object_unref: assertion 'G_IS_OBJECT (object)' failed
        print('disposing customData...')
        if self._pipeline is None:
            return
        self._pipeline.set_state(Gst.State.NULL)
        #self._pipeline.unref()

if __name__ == '__main__':
    print('declaring variables of classes inherits from Gst.Object that should be unreferenced')
    gst_bus = None
    customData = CustomData()
    
    # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.init
    print('initializing Gst...')
    Gst.init(None)

    if not customData.create_pipeline():
        customData.dispose()
        sys.exit(1)

    if not customData.build_pipeline():
        customData.dispose()
        sys.exit(1)

    customData.setup_source()

    if not customData.play_pipeline():
        customData.dispose()
        sys.exit(1)

    customData.listen_to_bus()

    print('disposing the customData...')
    customData.dispose()

    print('finished running a dynamic pipeline example')
