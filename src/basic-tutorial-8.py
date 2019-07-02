import sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstAudio, GLib, GstApp

# Amount of bytes we are sending in each buffer
CHUNK_SIZE = 1024
# Samples per second we are sending
SAMPLE_RATE = 44100

class CustomData():

    def __init__(self):

        self.pipeline = None

        self.app_source = None
        self.tee = None
        self.audio_queue = None
        self.audio_convert1 = None
        self.audio_resample = None
        self.audio_sink = None

        self.video_queue = None
        self.audio_convert2 = None
        self.visual = None
        self.video_convert = None
        self.video_sink = None
        self.app_queue = None
        self.app_sink = None

        self.bus = None

        # Number of samples generated so far (for timestamp generation) 
        self.num_samples = 0
        # For waveform generation
        self.a = 0
        self.b = 1
        self.c = 0
        self.d = 1

        # To control the GSource
        self.sourceid = 0

        # GLib's Main Loop
        self.main_loop = None

    def create_elements(self):

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.make
        print('creating elements...')
        self.app_source = Gst.ElementFactory.make("appsrc", "app_source")
        self.tee = Gst.ElementFactory.make("tee", "tee")

        self.audio_queue = Gst.ElementFactory.make("queue", "audio_queue")
        self.audio_convert1 = Gst.ElementFactory.make("audioconvert", "audio_convert1")
        self.audio_resample = Gst.ElementFactory.make("audioresample", "audio_resample")
        self.audio_sink = Gst.ElementFactory.make("autoaudiosink", "audio_sink")

        self.video_queue = Gst.ElementFactory.make("queue", "video_queue")
        self.audio_convert2 = Gst.ElementFactory.make("audioconvert", "audio_convert2")
        self.visual = Gst.ElementFactory.make("wavescope", "visual")
        self.video_convert = Gst.ElementFactory.make("videoconvert", "video_convert")
        self.video_sink = Gst.ElementFactory.make("autovideosink", "video_sink")

        self.app_queue = Gst.ElementFactory.make("queue", "app_queue")
        self.app_sink = Gst.ElementFactory.make("appsink", "app_sink")

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pipeline.html#Gst.Pipeline.new
        print('creating an empty pipeline')
        self.pipeline = Gst.Pipeline.new("test-pipeline")

        return not (
                self.app_source is None or self.tee is None or \
                self.audio_queue is None or self.audio_convert1 is None or self.audio_resample is None or self.audio_sink is None or \
                self.video_queue is None or self.audio_convert2 is None or self.visual is None or self.video_convert is None or self.video_sink is None or \
                self.app_queue is None or self.app_sink is None or self.pipeline is None)

    def setup_wavescope(self):
        # https://lazka.github.io/pgi-docs/#GObject-2.0/classes/Object.html#GObject.Object.set_property
        print('setting up wavescope...')
        self.visual.set_property('shader', 0)
        self.visual.set_property('style', 1)

    def configure_appsrc(self, audio_caps):

        print('configuring app_source...')
        
        self.app_source.set_property("caps", audio_caps)
        # https://lazka.github.io/pgi-docs/#GstApp-1.0/classes/AppSrc.html#GstApp.AppSrc.props.format
        self.app_source.set_property("format", Gst.Format.TIME)

        print('connecting to signals...')
        self.app_source.connect("need-data", self.start_feed)
        self.app_source.connect("enough-data", self.stop_feed)

    def configure_appsink(self, audio_caps):
        
        print('configuring app_sink...')

        self.app_sink.set_property("emit-signals", True)
        self.app_sink.set_property("caps", audio_caps)

        self.app_sink.connect("new-sample", self.new_sample)

    def link_always_pads(self):
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bin.html#Gst.Bin.add
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.link
        print('linking always pads...')
        self.pipeline.add(self.app_source)
        self.pipeline.add(self.tee)
        self.pipeline.add(self.audio_queue)
        self.pipeline.add(self.audio_convert1)
        self.pipeline.add(self.audio_resample)
        self.pipeline.add(self.audio_sink)
        self.pipeline.add(self.video_queue)
        self.pipeline.add(self.audio_convert2)
        self.pipeline.add(self.visual)
        self.pipeline.add(self.video_convert)
        self.pipeline.add(self.video_sink)
        self.pipeline.add(self.app_queue)
        self.pipeline.add(self.app_sink)
        if not self.app_source.link(self.tee) or not self.audio_queue.link(self.audio_convert1) or \
            not self.audio_convert1.link(self.audio_resample) or not self.audio_resample.link(self.audio_sink) or \
            not self.video_queue.link(self.audio_convert2) or not self.audio_convert2.link(self.visual) or \
            not self.visual.link(self.video_convert) or not self.video_convert.link(self.video_sink) or \
            not self.app_queue.link(self.app_sink):
            print('failed to link')
            pipeline.set_state(Gst.State.NULL)
            sys.exit(1)

    def link_request_pads(self):
        print('linking request pads...')
        tee_audio_pad = self.tee.get_request_pad("src_%u")
        queue_audio_pad = self.audio_queue.get_static_pad("sink")
        tee_video_pad = self.tee.get_request_pad("src_%u")
        queue_video_pad = self.video_queue.get_static_pad("sink")
        tee_app_pad = self.tee.get_request_pad("src_%u")
        queue_app_pad = self.app_queue.get_static_pad("sink")
        if not tee_audio_pad.link(queue_audio_pad) == Gst.PadLinkReturn.OK \
            or not tee_video_pad.link(queue_video_pad) == Gst.PadLinkReturn.OK \
            or not tee_app_pad.link(queue_app_pad) == Gst.PadLinkReturn.OK:
            print('tee could not be linked')
            pipeline.set_state(Gst.State.NULL)
            sys.exit(1)

    def setup_bus(self):
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_bus
        print('listening to the bus...')
        self.bus = self._pipeline.get_bus()
        self.bus.connect("message::error", self.error_cb)

    def play_pipeline(self):
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.set_state
        print('start playing the pipeline...')
        gst_state_change_return = self.pipeline.set_state(Gst.State.PLAYING)
        if gst_state_change_return == Gst.StateChangeReturn.FAILURE:
            print('failed to play')
            self.dispose()
            return False

        print('successfully played the pipeline')
        return True

    def run_main(self):
        print("running GLib main loop...")
        # https://lazka.github.io/pgi-docs/#GLib-2.0/classes/MainLoop.html#GLib.MainLoop
        # https://lazka.github.io/pgi-docs/#GLib-2.0/classes/MainLoop.html#GLib.MainLoop.run
        self.main_loop = GLib.MainLoop()
        self.main_loop.run()

    """
    This method is called by the idle GSource in the mainloop, to feed CHUNK_SIZE bytes into appsrc.
    The idle handler is added to the mainloop when appsrc requests us to start sending data (need-data signal)
    and is removed when appsrc has enough data (enough-data signal).
    """
    def push_data(self):
        print("push_data called")
        num_samples = CHUNK_SIZE // 2

        print('creating a buffer...')
        #https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Buffer.html#Gst.Buffer.new_allocate
        buf = Gst.Buffer.new_allocate(None, num_samples)
        # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.util_uint64_scale
        buf.pts = Gst.util_uint64_scale(self.num_samples, Gst.SECOND, SAMPLE_RATE)
        buf.duration = Gst.util_uint64_scale(num_samples, Gst.SECOND, SAMPLE_RATE)
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Buffer.html#Gst.Buffer.map
        success, info = buf.map(Gst.MapFlags.WRITE)
        if not success:
            print('failed to create a map')
            return False
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/MapInfo.html#Gst.MapInfo
        raw = list(info.data)
        self.c += self.d
        self.d -= self.c / 1000
        freq = 1100 + 1000 * self.d
        for i in range(num_samples):
            self.a += self.b
            self.b -= self.a / freq
            raw[i] = 500 * self.a
        self.num_samples += num_samples

        print('pushing the buffer to appsrc...')
        ret = self.app_source.emit("push-buffer", buf)
        if not ret == Gst.FlowReturn.OK:
            print('failed to push the buffer')
            return False

        return True

    """
    This signal callback triggers when appsrc needs data. Here, we add an idle handler
    to the mainloop to start pushing data into the appsrc
    """
    def start_feed(self, source, size):
        print("start_feed called")

        if self.sourceid == 0:
            print("start feeding...")
            # https://lazka.github.io/pgi-docs/#GLib-2.0/functions.html#GLib.idle_add
            self.sourceid = GLib.idle_add(self.push_data)

    """
    This callback triggers when appsrc has enough data and we can stop sending.
    We remove the idle handler from the mainloop
    """
    def stop_feed(self, source):
        print("stop_feed called")

        if self.sourceid != 0:
            print('stop feeding...')
            # https://lazka.github.io/pgi-docs/#GLib-2.0/functions.html#GLib.source_remove
            GLib.source_remove(self.sourceid)
            self.sourceid = 0

    """
    The appsink has received a buffer
    """
    def new_sample(self, sink):
        print("new_sample called")

        # https://lazka.github.io/pgi-docs/#GObject-2.0/classes/Object.html#GObject.Object.emit
        sample = self.app_sink.emit("pull-sample")
        if sample is not None:
            print('*{}*'.format(sample.get_buffer().get_size()))
            return Gst.FlowReturn.OK

        return Gst.FlowReturn.ERROR

    """
    This function is called when an error message is posted on the bus
    """
    def error_cb(self, bus, msg):
        print("error_cb called")

    def dispose(self):
        print('disposing customData...')
        if self.pipeline is None:
            return
        self.pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    data = CustomData()
    
    # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.init
    print('initializing Gst...')
    Gst.init(None)

    if not data.create_elements():
        print('failed to create elements nor a pipeline')
        sys.exit(1)

    data.setup_wavescope()

    # https://lazka.github.io/pgi-docs/#GstAudio-1.0/classes/AudioInfo.html#GstAudio.AudioInfo.set_format
    info = GstAudio.AudioInfo()
    info.set_format(GstAudio.AudioFormat.S16, SAMPLE_RATE, 1, None)
    # https://lazka.github.io/pgi-docs/#GstAudio-1.0/classes/AudioInfo.html#GstAudio.AudioInfo.to_caps
    audio_caps = info.to_caps()
    data.configure_appsrc(audio_caps)
    data.configure_appsink(audio_caps)

    data.link_always_pads()
    data.link_request_pads()

    if not data.play_pipeline():
        sys.exit(1)

    data.run_main()

    print('disposing the data...')
    data.dispose()

    print('finished running a short cutting the pipeline example')