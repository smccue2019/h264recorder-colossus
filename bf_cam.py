#!/usr/bin/env python
import sys, os, time, string, exceptions
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import gobject, pygst
gobject.threads_init()
pygst.require('0.10')
import gst

class bf_cam(QThread):

    new_clip = pyqtSignal(QString, name = 'new_clip')
    finished = pyqtSignal(QString, name = 'finished')
    stream_status = pyqtSignal(QString, name = 'stream_status')
    pipe_error = pyqtSignal(QString, name = 'pipe_error')

    def __init__(self,camera_device,camera_name,clip_duration,audio_dev,fsc):
        QThread.__init__(self, parent=None)
        self.camera_device = camera_device
        self.camera_name = camera_name
        self.clip_duration = clip_duration
        self.filesize_check_period = fsc
        self.audio_dev = audio_dev
        self.initiated = False
        self.growState = False

        # Growth calculation: basis = 580MB in 15 minutes.
        # Use 600KB per sec. Be conservative, make min size 80% of
        # calculated rate.
        self.min_growth_size = int(0.8 * (fsc * 600000))
        #self.min_growth_size = 570000000
        self.camfile_prefix = self.camera_name

        self.clip_timer = QTimer()
        self.clip_timer.timeout.connect(self.at_clip_timeout)

        self.filechecktimer = QTimer()
        self.filechecktimer.timeout.connect(self.at_filechecktimeout)
        self.growState = False

    def start_recording(self):
        if self.initiated == False:
            self.gen_outfilename()
            print self.camoutfile
            self.initiated = True
            self.clip_timer.start(self.clip_duration)

            self.reffilesize = 0
            self.filechecktimer.start(self.filesize_check_period * 1000.0)
            self.start()

    def stop_recording(self):
        if self.initiated == True:
            self.initiated = False
            self.growState = False
            self.clip_timer.stop()
            self.filechecktimer.stop()
            self.pipeline.set_state(gst.STATE_NULL)
            self.finished.emit(systime())

    def at_filechecktimeout(self):
#        print "\n ========= Recording health check at %s" % systimef_s()
        # SJM Set minimum growth rate.
        filesize = self.get_vidfilesize()
#        print "Needed growth: %d" % self.min_growth_size
#        print "New filesize: %d" % filesize
#        print "Former filesize: %d" % self.reffilesize
#        print "Expected minimum: %d" % (self.reffilesize + self.min_growth_size)
        if not filesize > self.reffilesize + self.min_growth_size:
            self.growState = False
            self.reffilesize = filesize
#            print "%s is NOT growing" % self.camoutfile
        elif filesize > self.reffilesize:
            self.growState = True
            self.reffilesize = filesize
#            print "%s IS growing: %d" % (self.camoutfile, filesize)
        else:
            "Something is up with outfile"

    def get_vidfilesize(self):
        return os.stat(self.camoutfile).st_size

    def isGrowing(self):
        return self.growState

    def isInitiated(self):
        return self.initiated

    def run(self):
        '''
Colossus parameters, obtained with 'v4l2-ctl --device=/dev/video0 -l'
brightness (int)    : min=0 max=255 step=1 default=0 value=128 flags=slider
contrast (int)    : min=0 max=255 step=1 default=128 value=128 flags=slider
saturation (int)    : min=0 max=255 step=1 default=128 value=128 flags=slider
hue (int)    : min=0 max=255 step=1 default=0 value=0 flags=slider
mute (bool)   : default=0 value=0
video_aspect (menu)   : min=1 max=2 default=2 value=2
video_bitrate_mode (menu)   : min=0 max=1 default=0 value=0 flags=update
video_bitrate (int)    : min=1000000 max=20000000 step=100000 default=5000000 value=5000000
video_peak_bitrate (int)    : min=1000000 max=20000000 step=100000 default=5000000 value=5000000
        '''

        # DO NOT set video input to HDMI, which is input '0'. It breaks
        # something.
        # Set audio input to RCA plugs so that lack of audio on HDMI pathway
        # doesn't confuse the HDMI video input (leads to dropped frames)
        set_audio= "%s%s %s%s" % ("v4l2-ctl -d ", self.camera_device, \
                                    "--set-audio-input=", self.audio_dev)
#        os.system(set_audio)

        self.pipeline = gst.Pipeline()
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect('message', self.on_message)

        self.source = gst.element_factory_make("v4l2src", "camera_device")
        self.source.set_property("device", self.camera_device)
        self.source.sync_state_with_parent()
        self.pipeline.add(self.source)

        self.save_queue = gst.element_factory_make("queue", "save_queue")
        self.save_queue.set_property("leaky", 0)
        self.save_queue.sync_state_with_parent()
        self.pipeline.add(self.save_queue)
        self.source.link(self.save_queue)

        self.filesink = gst.element_factory_make("filesink", "outfile")
        self.filesink.set_property("location", self.camoutfile)
        self.filesink.sync_state_with_parent()
        self.pipeline.add(self.filesink)
        self.save_queue.link(self.filesink)

        self.pipeline.set_state(gst.STATE_PLAYING)

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_STREAM_STATUS:
            self.stream_status.emit("stream_status(t)")
        elif t == gst.MESSAGE_EOS:
            self.stop_recording()
            return True
        elif t == gst.MESSAGE_ERROR:
            self.pipeline.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            self.pipeError.emit()

    def at_clip_timeout(self):
#        self.pipeline.send_event(gst.event.new_eos())
#        self.source.send_event(gst.event.new_eos())
        self.stop_recording()

    def gen_outfilename(self):
        self.camoutfile = "%s_%s.ts" % (self.camfile_prefix, systime())

    def get_camoutfile(self):
        return self.camoutfile

def systime():
    now = QDateTime.currentDateTime()
    systime = now.toString("yyyyMMddhhmmss.zz")
    return systime
def systimef():
    now = QDateTime.currentDateTime()
    systimef = now.toString("yyyy/MM/dd hh:mm:ss.zz")
    return systimef
