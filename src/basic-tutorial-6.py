import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

def print_field(field_id, value):
    # https://lazka.github.io/pgi-docs/#Gst-1.0/callbacks.html#Gst.StructureForeachFunc
    print('field_id, value = {}, {}'.format(field_id, value))

def print_caps(caps):
    
    if caps == None:
        print('no capabilities available')
    elif caps.is_any():
        print('Any capability')
    elif caps.is_empty():
        print('Empty capability')
    else:
        print('checking capabilities...')

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Caps.html#Gst.Caps.get_structure
        for i in range(caps.get_size()):
            pad_struct = caps.get_structure(i)
            print('{}'.format(pad_struct))
            # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Structure.html#Gst.Structure.foreach
            pad_struct.foreach(print_field)

def print_pad_templates_information(factory):
    
    print('printing pad templates of {} factory'.format(factory.name))

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.get_num_pad_templates
    num_pads = factory.get_num_pad_templates()
    if num_pads == 0:
        print('no pad template is available')
        return
    else:
        print('{} pad templates are available'.format(num_pads))

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.get_static_pad_templates
    pad_templates = factory.get_static_pad_templates()
    for pad_template in pad_templates:
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/StaticPadTemplate.html
        print('checking {}...'.format(pad_template.name_template))
        if pad_template.direction == Gst.PadDirection.SRC:
            print('checked the direction, Src pad')
        elif pad_template.direction == Gst.PadDirection.SINK:
            print('checked the direction, Sink pad')
        else:
            print('checked the direction, Unknown pad')

        # https://lazka.github.io/pgi-docs/#Gst-1.0/enums.html#Gst.PadPresence
        if pad_template.presence == Gst.PadPresence.ALWAYS:
            print('checked the presence, Always available')
        elif pad_template.presence == Gst.PadPresence.SOMETIMES:
            print('checked the presence, Sometimes available')
        elif pad_templates.presence == Gst.PadPresence.REQUEST:
            print('checked the presence, Upon request available')

        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/StaticCaps.html#Gst.StaticCaps
        print('capabilities: {}'.format(pad_template.static_caps.string))

def print_pad_capabilities(element, pad_name):
    
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_static_pad
    pad = element.get_static_pad(pad_name)
    print('checking {} from {}'.format(pad, element))

    print('checking the pad capabilities...')
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pad.html#Gst.Pad.get_current_caps
    caps = pad.get_current_caps()
    if caps is None:
        print('the pad has no caps, querying...')
        # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pad.html#Gst.Pad.query_capshttps://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pad.html#Gst.Pad.query_caps
        caps = pad.query_caps()
        return

    print_caps(caps)

if __name__ == '__main__':

    # https://lazka.github.io/pgi-docs/#Gst-1.0/functions.html#Gst.init
    print('initializing Gst...')
    Gst.init(None)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.find
    print('finding element factories...')
    source_factory = Gst.ElementFactory.find("audiotestsrc")
    sink_factory = Gst.ElementFactory.find("autoaudiosink")

    if source_factory is None or sink_factory is None:
        print('failed to create elements')
        sys.exit(1)

    print_pad_templates_information(source_factory)
    print_pad_templates_information(sink_factory)

    print('creating elements...')
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/ElementFactory.html#Gst.ElementFactory.create
    source = source_factory.create()
    sink = sink_factory.create()

    # limit the length
    source.set_property('num-buffers', 30)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Pipeline.html#Gst.Pipeline.new
    print('creating an empty pipeline')
    pipeline = Gst.Pipeline.new("test-pipeline")

    if source is None or sink is None or pipeline is None:
        print('failed to create elements or a pipeline')
        sys.exit(1)

    print('Print initial negotiated caps (in NULL state)')
    print_pad_capabilities(sink, 'sink')

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bin.html#Gst.Bin.add
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.link
    print('building the pipeline...')
    pipeline.add(source)
    pipeline.add(sink)
    if not source.link(sink):
        print('failed to link')
        pipeline.set_state(Gst.State.NULL)
        sys.exit(1)

    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.set_state
    print('start playing the pipeline...')
    gst_state_change_return = pipeline.set_state(Gst.State.PLAYING)
    if gst_state_change_return == Gst.StateChangeReturn.FAILURE:
        print('failed to play')
        pipeline.set_state(Gst.State.NULL)
        sys.exit(1)

    terminated = False
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Element.html#Gst.Element.get_bus
    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Bus.html#Gst.Bus.timed_pop_filtered
    print('listening to the bus...')
    bus = pipeline.get_bus()

    while not terminated:
        gst_message = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS)

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
                if gst_message.src == pipeline:
                    # https://lazka.github.io/pgi-docs/#Gst-1.0/classes/Message.html#Gst.Message.parse_state_changed
                    oldState, newState, pending = gst_message.parse_state_changed()
                    print('state changed from {} to {}'.format(oldState, newState))
                    print_pad_capabilities(sink, 'sink')
                else:
                    print('received a state change message {} from {}'.format(message_type, gst_message.src))
            else:
                print('this should not happen, the received message type is unexpectedly {}'.format(message_type))


    # set state NULL
    # call unref(), but which will leave many CRITICAL error messages as follows...
    # (python3:772): GLib-GObject-CRITICAL **: 08:49:46.297: g_object_unref: assertion 'G_IS_OBJECT (object)' failed
    print('disposing the pipeline...')
    pipeline.set_state(Gst.State.NULL)

    print('finished running pad capabilities example')