#!/usr/bin/env python3

from PIL import Image, ImageFont, ImageDraw
from font_hanken_grotesk import HankenGroteskBold, HankenGroteskMedium
from font_intuitive import Intuitive
from inky.auto import auto
from datetime import datetime

class InkyTrain():

    def __init__(self):
        #Configure the display for use
        #Set the img for drawing 
        #Autoconfigure the display detection
        self.inky_display = auto(ask_user=True, verbose=True)
        self.inky_display.h_flip = True
        self.inky_display.v_flip = True

    def draw_inbound_outbound(self, line, next_inbound_str, next_outbound_str):

        self.img = Image.new("P", (self.inky_display.WIDTH, self.inky_display.HEIGHT))
        self.draw = ImageDraw.Draw(self.img)
        
        if next_inbound_str != None:
            next_inbound_dt = datetime.fromisoformat(next_inbound_str)
            next_inbound = next_inbound_dt.strftime("%H:%M:%S")
        else:
            next_inbound = "Tomorrow"
        if next_outbound_str != None:    
            next_outbound_dt = datetime.fromisoformat(next_outbound_str)
            next_outbound = next_outbound_dt.strftime("%H:%M:%S")
        else:
            next_outbound = "Tomorrow"

        font_times = ImageFont.truetype(HankenGroteskBold, 20)
        font_line = ImageFont.truetype(HankenGroteskBold, 30)
        font_date = ImageFont.truetype(HankenGroteskBold, 25)

        line_text = line
        w_line, h_line = font_line.getsize(line_text)
        x_line = 10
        y_line = 0
        self.draw.text((x_line, y_line), line_text, self.inky_display.BLACK, font_line)

        today = datetime.now()
        date_text = today.strftime("%m/%d/%y")
        w_date, h_date = font_date.getsize(date_text)
        x_date = x_line + w_line + 4
        y_date = 0
        self.draw.text((x_date, y_date), date_text, self.inky_display.RED, font_date)

        inbound_message = "Next Inbound:    " + next_inbound
        w_inbound, h_inbound = font_line.getsize(inbound_message)
        x_inbound = 10
        y_inbound = h_line
        self.draw.text((x_inbound, y_inbound), inbound_message, self.inky_display.BLACK, font_times)
    
        outbound_message = "Next Outbound: " + next_outbound
        w_outbound, h_outbound = font_times.getsize(outbound_message)
        x_outbound = 10
        y_outbound = y_inbound + (h_inbound/2) + 4
        self.draw.text((x_outbound, y_outbound), outbound_message, self.inky_display.BLACK, font_times)

        self.inky_display.set_image(self.img)
        self.inky_display.show()

