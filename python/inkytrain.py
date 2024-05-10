from datetime import datetime
from PIL import Image, ImageFont, ImageDraw
from font_hanken_grotesk import HankenGroteskBold, HankenGroteskMedium
from inky.auto import auto

class InkyTrain():

    STANDARD_X_COORD = 10

    def __init__(self):
        #Configure the display for use
        #Set the img for drawing
        #Autoconfigure the display detection
        self.inky_display = auto(ask_user=True, verbose=True)
        self.inky_display.h_flip = True
        self.inky_display.v_flip = True

        self.img = Image.new("P", (self.inky_display.WIDTH, self.inky_display.HEIGHT))
        self.draw = ImageDraw.Draw(self.img)

    def draw_inbound_outbound(self, line, stop1, stop2, s1_next_inbound_str, s1_next_outbound_str, s2_next_inbound_str, s2_next_outbound_str):
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
        
        if s1_next_inbound_str is not None:
            s1_next_inbound_dt = datetime.fromisoformat(s1_next_inbound_str)
            s1_next_inbound = s1_next_inbound_dt.strftime("%I:%M%p")
        else:
            s1_next_inbound = "Tomorrow"
        if s1_next_outbound_str is not None:    
            s1_next_outbound_dt = datetime.fromisoformat(s1_next_outbound_str)
            s1_next_outbound = s1_next_outbound_dt.strftime("%I:%M%p")
        else:
            s1_next_outbound = "Tomorrow"
        if s2_next_inbound_str is not None:
            s2_next_inbound_dt = datetime.fromisoformat(s2_next_inbound_str)
            s2_next_inbound = s2_next_inbound_dt.strftime("%I:%M%p")
        else:
            s2_next_inbound = "Tomorrow"
        if s2_next_outbound_str is not None:
            s2_next_outbound_dt = datetime.fromisoformat(s2_next_outbound_str)
            s2_next_outbound = s2_next_outbound_dt.strftime("%I:%M%p")
        else:
            s2_next_outbound = "Tomorrow"

        font_times = ImageFont.truetype(HankenGroteskMedium, 18)
        font_stop_name = ImageFont.truetype(HankenGroteskBold, 20)
        font_line = ImageFont.truetype(HankenGroteskBold, 24)
        font_date = ImageFont.truetype(HankenGroteskBold, 20)

        #Which line we are displaying information for
        _left_line, _top_line, _right_line, bottom_line = font_line.getbbox(line)
        x_line = self.STANDARD_X_COORD
        y_line = 0
        self.draw.text((x_line, y_line), line, self.inky_display.BLACK, font_line)

        #Today's date
        today = datetime.now()
        date_text = today.strftime("%m/%d/%y")
        #Get the width of the display
        display_width = self.inky_display.resolution[0]
        length_date = font_stop_name.getlength(date_text)
        x_date = display_width - length_date
        y_date = 0
        self.draw.text((x_date, y_date), date_text, self.inky_display.RED, font_date)

        #Name of Stop 1
        y_pos = bottom_line #Start below the Line name
        stop1_x = self.STANDARD_X_COORD
        self.draw.text((stop1_x, y_pos), stop1, self.inky_display.BLACK, font_stop_name)
        _left_stop1, _top_stop1, _right_stop1, bottom_stop1 = font_stop_name.getbbox(stop1)
        y_pos = y_pos + (bottom_stop1)

        #Stop 1 inbound information
        s1_inbound_message = "Next Inbound:    " + s1_next_inbound
        s1_x_inbound = self.STANDARD_X_COORD
        self.draw.text((s1_x_inbound, y_pos), s1_inbound_message, self.inky_display.BLACK, font_times)
        _left_s1_inbound, _top_s1_inbound, _right_s1_inbound, bottom_s1_inbound = font_stop_name.getbbox(s1_inbound_message)
        y_pos = y_pos + (bottom_s1_inbound)
    
        #Stop 1 outbound information
        s1_outbound_message = "Next Outbound: " + s1_next_outbound
        _s1_x_outbound = self.STANDARD_X_COORD
        #self.draw.text((s1_x_outbound, y_pos), s1_outbound_message, self.inky_display.BLACK, font_times)
        #left_s1_outbound, top_s1_outbound, right_s1_outbound, bottom_s1_outbound = font_times.getbbox(s1_outbound_message)
        #y_pos = y_pos + (bottom_s1_outbound)

        #Stop 2 name
        stop2_x = self.STANDARD_X_COORD
        self.draw.text((stop2_x, y_pos), stop2, self.inky_display.BLACK, font_stop_name)
        _left_stop2, _top_stop2, _right_stop2, bottom_stop2 = font_stop_name.getbbox(stop2)
        y_pos = y_pos + (bottom_stop2)

        #Stop 2 inbound information
        s2_inbound_message = "Next Inbound:    " + s2_next_inbound
        s2_x_inbound = self.STANDARD_X_COORD
        self.draw.text((s2_x_inbound, y_pos), s2_inbound_message, self.inky_display.BLACK, font_times)
        _left_s2_inbound, _top_s2_inbound, _right_s2_inbound, bottom_s2_inbound = font_stop_name.getbbox(s2_inbound_message)
        y_pos = y_pos + (bottom_s2_inbound)
    
        #Stop 2 outbound information
        s2_outbound_message = "Next Outbound: " + s2_next_outbound
        s2_x_outbound = self.STANDARD_X_COORD
        self.draw.text((s2_x_outbound, y_pos), s2_outbound_message, self.inky_display.BLACK, font_times)
        _left_s2_outbound, _top_s2_outbound, _right_s2_outbound, bottom_s2_outbound = font_times.getbbox(s1_outbound_message)
        y_pos = y_pos + (bottom_s2_outbound)

        self.inky_display.set_image(self.img)
        self.inky_display.set_border(self.inky_display.BLACK)
        self.inky_display.show()

