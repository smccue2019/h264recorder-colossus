#!/usr/bin/env python
import sys, time, string, exceptions
from numpy import nan
from math import isnan
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from ConfigParser import SafeConfigParser
from CamDisplay_ui import Ui_CamDisplayMW

class cam_display(QMainWindow):

    def __init__(self, ini_file, parent=None):
	QWidget.__init__(self,parent)
        self.ui = Ui_CamDisplayMW()
        self.ui.setupUi(self)
        self.ui.quitButton.clicked.connect(self.on_quit_button)
        self.ui.startButton.clicked.connect(self.on_start_button)
        self.ui.stopButton.clicked.connect(self.on_stop_button)

        # Behavior params must be set in a config file, named in __main__
        # Other behaviors set here.
        self.do_init(ini_file)    
        self.ui.MetadataDisplay.LineWrapMode(1)
        self.smoothed_alt = 1000.0

        # Set up a timer that interrogates system for its time, then
        # updates the display of that time.

        self.clockdisplaytimer = QTimer()
        self.clockdisplaytimer.timeout.connect(self.update_displays)

        self.vr1=bf_cam(self.camera1_device,self.camera1_name,self.clip_duration,self.audiodev, self.filesize_check_period)
        self.ui.Cam1Name.setText(self.camera1_name)
        self.vr1.new_clip.connect(self.on_new_clip1)
        self.vr1.finished.connect(self.on_pipe1_finished)
        self.vr1.stream_status.connect(self.on_status_signal1)
        self.vr1.pipe_error.connect(self.on_pipe1_error)

        self.vr2=bf_cam(self.camera2_device,self.camera2_name,self.clip_duration,self.audiodev, self.filesize_check_period)
        self.ui.Cam2Name.setText(self.camera2_name)
        self.vr2.new_clip.connect(self.on_new_clip2)
        self.vr2.finished.connect(self.on_pipe2_finished)
        self.vr2.stream_status.connect(self.on_status_signal2)
        self.vr2.pipe_error.connect(self.on_pipe2_error)

        self.vr3=bf_cam(self.camera3_device,self.camera3_name,self.clip_duration,self.audiodev, self.filesize_check_period)
        self.ui.Cam3Name.setText(self.camera3_name)
        self.vr3.new_clip.connect(self.on_new_clip3)
        self.vr3.finished.connect(self.on_pipe3_finished)
        self.vr3.stream_status.connect(self.on_status_signal3)
        self.vr3.pipe_error.connect(self.on_pipe3_error)


        # Set up a listener that captures Jason Data String (JDS) an
        # O___ Data Records (ODR) UDP packets that are broadcast on
        # JasonNet during operations. From these packets:
        #   1. extract vehicle altitude above bottom, which is used to
        #      control whether recording is off or on.
        #   2. pass the full packets to an object that merges and morphs
        #      them into a form suitable for tagging the video w/ metadata. 
        self.meta_receiver=UDPreceiver(self.ListenPort)
        self.meta_receiver.new_altitude.connect(self.on_new_altitude)
        self.meta_receiver.new_jds.connect(self.on_new_jds) 
        self.meta_receiver.new_odr.connect(self.on_new_odr)
        self.meta_receiver.new_csv.connect(self.on_new_csv)

        self.dvl_alt=UDPreceiver(self.pwhdop_port)
        self.dvl_alt.new_pwhdop.connect(self.on_new_pwhdop)

        # UDP2subtitle both logs subtitles to a file and generates
        # displayable strings. Three lines.
        self.subtitleGen = UDP2subtitle()
        self.meta_receiver.new_jds.connect(self.subtitleGen.updateJDS)
        self.meta_receiver.new_odr.connect(self.subtitleGen.updateODR)
        self.subtitleGen.new_meta.connect(self.on_new_meta)

        self.send_stat = UDP_sendStatus(self.remoteStatusPort,self.remoteStatusIP)
        self.clockdisplaytimer.start(1000)

############ Assign initial conditions, also read external config file. #######

    def do_init(self, config_file):
        self.remoteStatusIP="198.17.154.206"
        self.remoteStatusPort=10520

        self.allowAltControl = False
        self.keepRecordStatus = True
#        self.descent_tracker = 0
#        self.ascent_tracker = 0
        self.dvl_lock_status = 0
        self.dvl_lock_str=""
        self.new_pwhdop = nan  # just to get started
        self.altf = nan  # just to get started
        self.ui.idleChoice1.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        self.ui.idleChoice2.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        self.ui.idleChoice3.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        self.ui.notGrowingChoice1.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
        self.ui.growChoice1.setStyleSheet("QLabel {background: rgb(255, 255, 255)}")
        self.ui.notGrowingChoice2.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
        self.ui.growChoice2.setStyleSheet("QLabel {background: rgb(255, 255, 255)}")
        self.ui.notGrowingChoice3.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
        self.ui.growChoice3.setStyleSheet("QLabel {background: rgb(255, 255, 255)}")


        ini_parser = SafeConfigParser()
        ini_parser.read(config_file)

        clip_minutes = num(ini_parser.get('Recording','clip_len'))
        self.clip_duration = clip_minutes * 60.0 * 1000.0
        self.filesize_check_period = num(ini_parser.get('Recording','filesize_check_period'))
        self.use_altitude = ini_parser.get('Recording','use_altitude')
        self.num_cards = num(ini_parser.get('Cards','CardCount'))
        self.camera1_device = ini_parser.get('Card1','camera1_device')
        self.camera1_name = ini_parser.get('Card1','camera1_name')
        self.camera2_device = ini_parser.get('Card2','camera2_device')
        self.camera2_name = ini_parser.get('Card2','camera2_name')
        self.camera3_device = ini_parser.get('Card3','camera3_device')
        self.camera3_name = ini_parser.get('Card3','camera3_name')
        self.audiodev = ini_parser.get('Cards','audiodev')
        self.ListenPort = num(ini_parser.get('Network','ListenPort'))
        self.pwhdop_port = num(ini_parser.get('Network','PwhdopPort'))
        self.reference_altitude = num(ini_parser.get('Network','reference_altitude'))
        self.descent_threshold = num(ini_parser.get('Recording','descent_threshold'))
        self.ascent_threshold = num(ini_parser.get('Recording','ascent_threshold'))

#       self.ui.altUseChackbox.checkStateSet(self.use_altitude)
######################## Signal Handling Routines ###################

# Make vr1 the master controller for subtitle generation. Let the others
# do something only of vr1 is not in a good state for control.
    def on_pipe1_finished(self, fin_timestr):
        self.subtitleGen.stop_logging()
        if self.keepRecordStatus == True:
            if self.vr1.isInitiated() == False:
                print "%s clip rollover at %s" % \
                    (self.camera1_name, fin_timestr)
                self.vr1.start_recording()
                self.subtitleGen.start_logging()
            else:
                print "Some kind of problem. Stop recording %s." % self.camera1_name
                self.vr1.stop_recording()
        else:
            self.ui.RecordingPathName1.setText("Recording pipeline finished")

    def on_pipe2_finished(self, fin_timestr):
#        self.subtitleGen.stop_logging()
        if self.keepRecordStatus == True:
            if self.vr2.isInitiated() == False:
                print " %s clip rollover at %s" % \
                    (self.camera2_name, fin_timestr)
                self.vr2.start_recording()
#                self.subtitleGen.start_logging()
            else:
                print "Some king of problem. Stop recording."
                self.vr2.stop_recording()
        else:
            self.ui.RecordingPathName2.setText("Recording pipeline finished")

    def on_pipe3_finished(self, fin_timestr):
#        self.subtitleGen.stop_logging()
        if self.keepRecordStatus == True:
            if self.vr3.isInitiated() == False:
                print "%s clip rollover at %s" % \
                    (self.camera3_name, fin_timestr)
                self.vr3.start_recording()
#                self.subtitleGen.start_logging()
            else:
                print "Some king of problem. Stop recording."
                self.vr3.stop_recording()
        else:
            self.ui.RecordingPathName3.setText("Recording pipeline finished")

    def update_displays(self):
        self.ui.ClockDisplay.setText(systimef_s())
        ############################ Camera 1 ##############################
        if self.vr1.isInitiated() == False: 
            self.ui.idleChoice1.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
            self.ui.recordChoice1.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
            self.send_stat.sendStatus(0)
        elif self.vr1.isInitiated() == True: 
            self.ui.idleChoice1.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
            self.ui.recordChoice1.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
            self.send_stat.sendStatus(1)
        else:
            pass

        if self.vr1.isGrowing() == False:
            self.ui.notGrowingChoice1.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
            self.ui.growChoice1.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
        elif self.vr1.isGrowing() == True:
            self.ui.notGrowingChoice1.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
            self.ui.growChoice1.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        else:
            pass

        ############################ Camera 2 ##############################
        if self.vr2.isInitiated() == False: 
            self.ui.idleChoice2.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
            self.ui.recordChoice2.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
        elif self.vr2.isInitiated() == True: 
            self.ui.idleChoice2.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
            self.ui.recordChoice2.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        else:
            pass

        if self.vr2.isGrowing() == False:
            self.ui.notGrowingChoice2.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
            self.ui.growChoice2.setStyleSheet("QLabel {background: rgb(0,0,0)}")
        elif self.vr2.isGrowing() == True:
            self.ui.notGrowingChoice2.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
            self.ui.growChoice2.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        else:
            pass

        ############################ Camera 1 ##############################
        if self.vr3.isInitiated() == False: 
            self.ui.idleChoice3.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
            self.ui.recordChoice3.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
        elif self.vr3.isInitiated() == True: 
            self.ui.idleChoice3.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
            self.ui.recordChoice3.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        else:
            pass

        if self.vr3.isGrowing() == False:
            self.ui.notGrowingChoice3.setStyleSheet("QLabel {background: rgb(255,153,51)}")
            self.ui.growChoice3.setStyleSheet("QLabel {background: rgb(0,0,0)}")
        elif self.vr3.isGrowing() == True:
            self.ui.notGrowingChoice3.setStyleSheet("QLabel {background: rgb(0, 0, 0)}")
            self.ui.growChoice3.setStyleSheet("QLabel {background: rgb(255, 153, 51)}")
        else:
            pass

    # Use vr1 as the trigger for generating new subtitle files 
    def on_new_clip1(self, cam1outfilename):
        self.ui.RecordingPathName1.setText(self.vr1.get_camoutfile())
        self.subtitleGen.new_clip()

    def on_new_clip2(self, cam2outfilename):
        self.ui.RecordingPathName2.setText(self.vr2.get_camoutfile())

    def on_new_clip3(self, cam3outfilename):
         self.ui.RecordingPathName3.setText(self.vr3.get_cam3outfile())

    def on_new_jds(self, new_jds):
#        self.ui.UDPDisplay.appendPlainText(new_jds)
        self.subtitleGen.updateJDS(new_jds)

    def on_new_odr(self, new_odr):
#        self.ui.UDPDisplay.appendPlainText(new_odr)
        self.subtitleGen.updateODR(new_odr)

    def on_new_csv(self, new_odr):
#        self.ui.UDPDisplay.appendPlainText(new_csv)
        pass

    def on_new_pwhdop(self, new_pwhdop, new_dvl_lock_status):
        self.new_pwhdop = new_pwhdop
        self.dvl_lock_status = new_dvl_lock_status
        dvl_lock_str = dvl_lock_stat2str(new_dvl_lock_status)
        lstr = "new DVL altitude is %6.2f, %s" % (self.new_pwhdop, dvl_lock_str)
#        self.ui.UDPDisplay.appendPlainText(lstr)

    def on_new_meta(self):

        str1 = "s1: %s" % (self.subtitleGen.get_metastr1())
        str2 = "s2: %s" % (self.subtitleGen.get_metastr2())
        str3 = "s3: %s" % (self.subtitleGen.get_metastr3())
        str4 = "s4: %s" % (self.subtitleGen.get_metastr4())
        self.ui.MetadataDisplay.appendPlainText(str1)
        self.ui.MetadataDisplay.appendPlainText(str2)
        self.ui.MetadataDisplay.appendPlainText(str3)
        self.ui.MetadataDisplay.appendPlainText(str4)
        
    def on_pipe1_error(self):
        self.ui.RecordingPathName1.setText("Recording pipeline error")

    def on_pipe2_error(self):
        self.ui.RecordingPathName2.setText("Recording pipeline error")

    def on_pipe3_error(self):
        self.ui.RecordingPathName3.setText("Recording pipeline error")

    def on_status_signal1(self):
        self.ui.RecordingPathName1.setText("Stream status message")

    def on_status_signal2(self):
        self.ui.RecordingPathName2.setText("Stream status message")

    def on_status_signal3(self):
        self.ui.RecordingPathName3.setText("Stream status message")

    def on_quit_button(self):
        self.vr1.stop_recording()
        self.vr2.stop_recording()
        self.vr3.stop_recording()
        self.subtitleGen.stop_logging()
        QCoreApplication.exit()

    def on_start_button(self):
        self.allowAltControl = False
        self.vr1.start_recording()
        self.vr2.start_recording()
        self.vr3.start_recording()
        self.subtitleGen.start_logging()
        self.ui.RecordingPathName1.setText(self.vr1.get_camoutfile())
        self.ui.RecordingPathName2.setText(self.vr2.get_camoutfile())
        self.ui.RecordingPathName3.setText(self.vr3.get_camoutfile())

    def on_stop_button(self):
        self.allowAltControl = True
        self.vr1.stop_recording()
        self.vr2.stop_recording()
        self.vr3.stop_recording()
        self.subtitleGen.stop_logging()
        self.ui.RecordingPathName1.setText("Manual stop")
        self.ui.RecordingPathName2.setText("Manual stop")
        self.ui.RecordingPathName3.setText("Manual stop")

    def on_altUseCheckbox_change(self):
        newState = self.ui.altUseCheckbox.checkState()
        print newState

# SJM Sept 2015
#    def on_new_altitude(self, new_altitude, new_depth):
    def on_new_altitude(self, new_altitude):

        if self.allowAltControl == True:
            # Pre-process the altitude to try and get a dependable value.
            # The altimter is too noisy near the bottom to use directly.

            # SJM Sept 2015 change complex mix of DVL and altimeter for just
            # altimeter. We recently switched to navest and navest does not
            # produce a PWHDOP packet. Also, I think applying a smoothing 
            # filter to altimeter and using start/stop hysteresis will make
            # things better than the crappy algoritm I had before.
#            app = preprocAltitude(new_altitude, self.new_pwhdop, self.dvl_lock_status)
            # Smoothing algorithm needs prior smoothed value of altitude and latest
            # altimiter measurement.
            alpha = 0.5
            app = preprocAltitude(alpha)
            app.update_alt_smoother(new_altitude, self.smoothed_alt)
            self.smoothed_alt = app.get_new_alt()

            if isnan(self.smoothed_alt):
                # Maintain recording status, display NaN result on UI
                self.ui.AltitudeDisplay.setText('NaN')
            else:
                # Use altitude to control recorder function. If the vehicle
                # has descended to below the reference altitude, turn on
                # the recorder. If the vehicle has ascended to above the
                # reference threshold plus a hysteresis value, turn off the
                # recorder.

                self.altitude = "%5.1f" % self.smoothed_alt
                self.ui.AltitudeDisplay.setText(self.altitude)

                # Control the GUI to indicate which source is provided altitude
                if self.use_altitude == False:
                    self.ui.altimeterChoice.setStyleSheet("QLabel {background: rgb(128, 128, 128)}")
                    self.ui.dopplerChoice.setStyleSheet("QLabel {background: rgb(128, 128, 128)}")
                else:
                    if app.get_alt_src() == 'Altimeter':
                        self.ui.altimeterChoice.setStyleSheet("QLabel {background: rgb(0, 255, 0)}")
                        self.ui.dopplerChoice.setStyleSheet("QLabel {background: rgb(255, 255, 255)}")
                    elif app.get_alt_src() == 'DVL':
                        self.ui.altimeterChoice.setStyleSheet("QLabel {background: rgb(255, 255, 255)}")
                        self.ui.dopplerChoice.setStyleSheet("QLabel {background: rgb(0, 255, 0)}")  
                    else:
                        self.ui.altimeterChoice.setStyleSheet("QLabel {background: rgb(255, 255, 255)}")
                        self.ui.dopplerChoice.setStyleSheet("QLabel {background: rgb(255, 255, 255)}")

                # Apply hysteresis to smoothed_altitude
                # Turn on at reference altitude
                # Turn off at reference altitude plus 10 meters
                if self.smoothed_alt <= self.reference_altitude:
                    if self.vr1.isInitiated() == False:
                        self.keepRecordStatus = True
                        self.vr1.start_recording()
                        self.vr2.start_recording()
                        self.vr3.start_recording()
                        self.subtitleGen.start_logging()
                        self.ui.RecordingPathName1.setText(self.vr1.get_camoutfile())
                        self.ui.RecordingPathName2.setText(self.vr2.get_camoutfile())
                        self.ui.RecordingPathName3.setText(self.vr3.get_camoutfile())
                        self.ui.AltitudeDisplay.setStyleSheet("QLabel {color: rgb(0, 255, 0)}")
                    elif self.vr1.isInitiated() == True:
                        pass
                    else:
                        pass
                elif self.smoothed_alt >= self.reference_altitude + 10:
                    # the ascending case, or at least the above ref alt case
                    if self.vr1.isInitiated() == True:
                        self.keepRecordStatus = False
                        self.vr1.stop_recording()
                        self.vr2.stop_recording()
                        self.vr3.stop_recording()
                        self.subtitleGen.stop_logging()
                        self.ui.AltitudeDisplay.setStyleSheet("QLabel {color: rgb(0, 0, 0)}")
                    elif self.vr1.isInitiated() == False:
                        pass
                    else:
                        pass

######################## Utility Routines #####################

def num (s):
    try:
        return int(s)
    except ValueError as e:
        return float(s)

def dvl_lock_stat2str(stat):
     if stat == 0:
         str = "None"
     elif stat == 1:
         str = "bottom_lock"
     elif stat == 2:
         str = 'water_lock'
     else:
         pass

######################## Main ################################
        
if __name__ == '__main__':

    config_file = 'cam.ini'
    
    try:
        execfile("bf_cam.py")
    except Exception as e:
        print "error opening or running cam.py", e

    try:
        execfile("udp_receiver.py")
    except Exception as e:
        print "error opening or running udp_receiver.py", e

    try:
        execfile("udp2subtitle.py")
    except Exception as e:
        print "error opening or running udp2subtitle.py", e

    try:
        execfile("preprocAltitude.py")
    except Exception as e:
        print "error opening or running preprocAltitude", e

    try:
        execfile("time_routines.py")
    except Exception as e:
        print "error opening or running time_routines", e

    try:
        execfile("udp_sender.py")
    except Exception as e:
        print "error opening or running udp_sender", e

    qapp = QApplication(sys.argv)

    os.system("v4l2-ctl -d /dev/video0 --set-audio-input=2")
    os.system("v4l2-ctl -d /dev/video1 --set-audio-input=2")
    os.system("v4l2-ctl -d /dev/video2 --set-audio-input=2")

    ver1 = cam_display(config_file)

    ver1.show()

    sys.exit(qapp.exec_())
