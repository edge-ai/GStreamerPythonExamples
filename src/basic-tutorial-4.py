import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

class CustomData():

    def __init__(self):
        self._playbin = None
        self._playing = False
        self._seek_enabled = False
        self._seek_done = False
        self._duration = Gst.CLOCK_TIME_NONE
        self._terminate = False

        self._bus = None
        self._current = None

    def create_pipeline(self):
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.make
        print('creating elements...')
        self._playbin = Gst.ElementFactory.make("playbin", "playbin")

        if self._playbin is None:
            print('failed to create a playbin')
            return False

        print('successfully created a playbin')
        return True

    def setup_source(self):
        # https://lazka.github.io/pgi-docs/#GObject-2.0/classes/Object.html#GObject.Object.set_property
        print('modifying the source properties...')
        self._playbin.set_property('uri', 'https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm')

    def play_pipeline(self):
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.set_state
        print('start playing the pipeline...')
        gst_state_change_return = self._playbin.set_state(Gst.State.PLAYING)
        if gst_state_change_return == Gst.StateChangeReturn.FAILURE:
            print('failed to play')
            self.dispose()
            return False

        print('successfully played the pipeline')
        return True

    def handle_message(self, gst_message):
        message_type = gst_message.type
        if message_type == Gst.MessageType.ERROR:
            gerror, debug = gst_message.parse_error()
            print('error {} happened at {}'.format(gerror.message, debug))
            self._terminate = True
        elif message_type == Gst.MessageType.EOS:
            print('EOS reached')
            self._terminate = True
        elif message_type == Gst.MessageType.DURATION_CHANGED:
            print('duration changed')
            # The duration has changed, mark the current one as invalid
            self._duration = Gst.CLOCK_TIME_NONE
        elif message_type == Gst.MessageType.STATE_CHANGED:
            # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Message.html#Gst.Message.parse_state_changed
            oldState, newState, pending = gst_message.parse_state_changed()
            if gst_message.src == self._playbin:
                print('playbin state changed from {} to {}'.format(oldState, newState))
                self._playing = newState == Gst.State.PLAYING

                if self._playing:
                    #We just moved to PLAYING. Check if seeking is possible
                    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.query
                    query = Gst.Query.new_seeking(Gst.Format.TIME)
                    if self._playbin.query(query):
                        fmt, self._seek_enabled, start, end = query.parse_seeking()
                        if self._seek_enabled:
                            print('seeking is enabled')
                        else:
                            print('seeking is disabled')
                    else:
                        print('seeking query failed')
        else:
            print('this should not happen, the received message type is unexpectedly {}'.format(message_type))

    def listen_to_bus(self):

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_bus
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bus.html#Gst.Bus.timed_pop_filtered
        print('listening to the bus...')
        self._bus = self._playbin.get_bus()

        while not self._terminate:
            gst_message = self._bus.timed_pop_filtered(100 * Gst.MSECOND, Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.DURATION_CHANGED)

            if gst_message is not None:

                self.handle_message(gst_message)

            else:

                # We got no message, this means the timeout expired
                if self._playing:

                    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.query_position
                    # Query the current position of the stream
                    queried, self._current = self._playbin.query_position(Gst.Format.TIME)
                    if not queried:
                        print('can not get the current position')
                        continue

                    if self._duration == Gst.CLOCK_TIME_NONE:
                        queried, self._duration = self._playbin.query_duration(Gst.Format.TIME)
                        if not queried:
                            print('can not get the duration')
                            continue

                    print('current position = {}, the duration = {}'.format(self._current, self._duration))

                    # If seeking is enabled, we have not done it yet, and the time is right, seek
                    if self._seek_enabled and not self._seek_done and self._current > 10 * Gst.SECOND:
                        print('reached 10s, performing seek...')
                        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.seek_simple
                        if self._playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 30 * Gst.SECOND):
                            print('seek succeeded')
                            self._seek_done = True
                        else:
                            print('seek failed')
                            self._seek_done = False


    def dispose(self):
        # not call unref(), but which will leave many CRITICAL error messages as follows...
        # (python3:772): GLib-GObject-CRITICAL **: 08:49:46.297: g_object_unref: assertion 'G_IS_OBJECT (object)' failed
        print('disposing customData...')
        if self._playbin is None:
            return
        self._playbin.set_state(Gst.State.NULL)
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

    customData.setup_source()

    if not customData.play_pipeline():
        customData.dispose()
        sys.exit(1)

    customData.listen_to_bus()

    print('disposing the customData...')
    customData.dispose()

    print('finished running a dynamic pipeline example')