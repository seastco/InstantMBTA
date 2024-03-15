#!/usr/bin/env python3

from PIL import Image, ImageFont, ImageDraw
from font_hanken_grotesk import HankenGroteskBold, HankenGroteskMedium
from inky.auto import auto
from datetime import datetime

class InkyTrain():

    STANDARD_X_COORD = 10

    def __init__(self):
        #Configure the display for use
        #Set the img for drawing 
        #Autoconfigure the display detection
        self.inky_display = auto(ask_user=True, verbose=True)
        self.inky_display.h_flip = True
        self.inky_display.v_flip = True

    """
    Draw the content on the screen of the Inky
    We start from top to bottom to better manage vertical locations
    At this time the display is capable of displaying information for two stops.
    The second stop can only display the outbound information (eol)
    This is due to space limitations on the screen while keeping things legible.
    line: The overall line that we are displaying
    stop1: The name of the first stop to display (inbound and outbound)
    stop2: The name of the second stop to display (outbound)
    s1_next_inbound_str: The time as a string for stop1 next inbound
    s1_next_outbound_str: The time as a string for stop1 next outbound
    s2_next_inbound_str: The time as a string for stop2 next inbound (unused right now)
    s2_next_outbound_str: The time as a string for stop2 next outbound
    """
    def draw_inbound_outbound(self, line, stop1, stop2, s1_next_inbound_str, s1_next_outbound_str, s2_next_inbound_str, s2_next_outbound_str):

        self.img = Image.new("P", (self.inky_display.WIDTH, self.inky_display.HEIGHT))
        self.draw = ImageDraw.Draw(self.img)
        
        if s1_next_inbound_str != None:
            s1_next_inbound_dt = datetime.fromisoformat(s1_next_inbound_str)
            s1_next_inbound = s1_next_inbound_dt.strftime("%I:%M%p")
        else:
            s1_next_inbound = "Tomorrow"
        if s1_next_outbound_str != None:    
            s1_next_outbound_dt = datetime.fromisoformat(s1_next_outbound_str)
            s1_next_outbound = s1_next_outbound_dt.strftime("%I:%M%p")
        else:
            s1_next_outbound = "Tomorrow"
        if s2_next_inbound_str != None:
            s2_next_inbound_dt = datetime.fromisoformat(s2_next_inbound_str)
            s2_next_inbound = s2_next_inbound_dt.strftime("%I:%M%p")
        else:
            s2_next_inbound = "Tomorrow"
        if s2_next_outbound_str != None:
            s2_next_outbound_dt = datetime.fromisoformat(s2_next_outbound_str)
            s2_next_outbound = s2_next_outbound_dt.strftime("%I:%M%p")
        else:
            s2_next_outbound = "Tomorrow"

        font_times = ImageFont.truetype(HankenGroteskMedium, 18)
        font_stop_name = ImageFont.truetype(HankenGroteskBold, 20)
        font_line = ImageFont.truetype(HankenGroteskBold, 30)
        font_date = ImageFont.truetype(HankenGroteskBold, 18)

        #Which line we are displaying information for
        line_text = line
        w_line, h_line = font_line.getsize(line_text)
        x_line = self.STANDARD_X_COORD
        y_line = 0
        self.draw.text((x_line, y_line), line_text, self.inky_display.ORANGE, font_line)

        #Today's date
        today = datetime.now()
        date_text = today.strftime("%m/%d/%y")
        w_date, h_date = font_date.getsize(date_text)
        x_date = x_line + w_line + 4
        y_date = 0
        self.draw.text((x_date, y_date), date_text, self.inky_display.RED, font_date)

        #Name of Stop 1
        y_pos = stop1_y = h_line
        stop1_x = self.STANDARD_X_COORD
        stop1_w, stop1_h = font_stop_name.getsize(stop1)
        self.draw.text((stop1_x, stop1_y), stop1, self.inky_display.BLACK, font_stop_name)

        #Stop 1 inbound information
        s1_inbound_message = "Next Inbound:    " + s1_next_inbound
        s1_w_inbound, s1_h_inbound = font_times.getsize(s1_inbound_message)
        s1_x_inbound = self.STANDARD_X_COORD
        y_pos = y_pos + (s1_h_inbound)
        self.draw.text((s1_x_inbound, y_pos), s1_inbound_message, self.inky_display.BLACK, font_times)
    
        #Stop 1 outbound information
        s1_outbound_message = "Next Outbound: " + s1_next_outbound
        s1_w_outbound, s1_h_outbound = font_times.getsize(s1_outbound_message)
        s1_x_outbound = self.STANDARD_X_COORD
        #y_pos = y_pos + (s1_h_outbound)
        #self.draw.text((s1_x_outbound, s1_y_outbound), s1_outbound_message, self.inky_display.BLACK, font_times)

        #Stop 2 name
        stop2_w, stop2_h = font_stop_name.getsize(stop2)
        stop2_x = self.STANDARD_X_COORD
        y_pos = y_pos + (stop2_h)
        self.draw.text((stop2_x, y_pos), stop2, self.inky_display.BLACK, font_stop_name)

        #Stop 2 inbound information
        s2_inbound_message = "Next Inbound:    " + s2_next_inbound
        s2_w_inbound, s2_h_inbound = font_times.getsize(s2_inbound_message)
        s2_x_inbound = self.STANDARD_X_COORD
        y_pos = y_pos + (s2_h_inbound)
        self.draw.text((s2_x_inbound, y_pos), s2_inbound_message, self.inky_display.BLACK, font_times)
    
        #Stop 2 outbound information
        s2_outbound_message = "Next Outbound: " + s2_next_outbound
        s2_w_outbout, s2_h_outbound = font_times.getsize(s2_outbound_message)
        s2_x_outbound = self.STANDARD_X_COORD
        y_pos = y_pos + (s2_h_outbound)
        self.draw.text((s2_x_outbound, y_pos), s2_outbound_message, self.inky_display.BLACK, font_times)

        self.inky_display.set_image(self.img)
        self.inky_display.show()

