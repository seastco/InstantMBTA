from datetime import datetime, timezone
from PIL import Image, ImageFont, ImageDraw
from font_hanken_grotesk import HankenGroteskBold, HankenGroteskMedium
from inky.auto import auto

class InkyTrain():

    STANDARD_X_COORD = 10
    MAX_LINES = 8  # Maximum lines that fit on the display

    def __init__(self):
        #Configure the display for use
        #Set the img for drawing
        #Autoconfigure the display detection
        self.inky_display = auto(ask_user=True, verbose=True)
        self.inky_display.h_flip = True
        self.inky_display.v_flip = True

    def draw_from_display_data(self, display_data):
        """
        Draw content from DisplayData object.
        This is the new preferred method that works with all display modes.
        
        Args:
            display_data: DisplayData object with formatted lines
        """
        img = Image.new("P", (self.inky_display.WIDTH, self.inky_display.HEIGHT))
        draw = ImageDraw.Draw(img)
        
        # Fonts
        font_title = ImageFont.truetype(HankenGroteskBold, 24)
        font_date = ImageFont.truetype(HankenGroteskBold, 20)
        font_header = ImageFont.truetype(HankenGroteskBold, 20)
        font_text = ImageFont.truetype(HankenGroteskMedium, 18)
        font_text_small = ImageFont.truetype(HankenGroteskMedium, 16)
        
        y_pos = 0
        
        # Draw title if present
        if display_data.title:
            draw.text((self.STANDARD_X_COORD, y_pos), 
                     display_data.title, 
                     self.inky_display.BLACK, 
                     font_title)
            _, _, _, bottom = font_title.getbbox(display_data.title)
            y_pos += bottom + 2
        
        # Draw date on the right
        if display_data.date:
            date_width = font_date.getlength(display_data.date)
            x_date = self.inky_display.WIDTH - date_width - 10
            draw.text((x_date, 0), 
                     display_data.date, 
                     self.inky_display.RED, 
                     font_date)
        
        # Draw lines
        line_count = 0
        for line in display_data.lines:
            if line_count >= self.MAX_LINES:
                break
                
            # Skip drawing if we're near the bottom
            if y_pos > self.inky_display.HEIGHT - 25:
                break
            
            # Select font based on line type
            if line.is_header:
                font = font_header
                color = self.inky_display.BLACK
                x_pos = self.STANDARD_X_COORD
            elif line.is_route:
                font = font_text
                color = self.inky_display.BLACK
                x_pos = self.STANDARD_X_COORD
            else:
                # Use smaller font if we have many lines
                if len(display_data.lines) > 6:
                    font = font_text_small
                else:
                    font = font_text
                color = self.inky_display.BLACK
                x_pos = self.STANDARD_X_COORD + (20 if line.indent else 0)
            
            # Draw the line
            if line.text.strip():  # Only draw non-empty lines
                draw.text((x_pos, y_pos), line.text, color, font)
                _, _, _, bottom = font.getbbox(line.text)
                y_pos += bottom + 2
            else:
                # Empty line - add some spacing
                y_pos += 10
            
            line_count += 1
        
        # Update display
        self.inky_display.set_image(img)
        self.inky_display.set_border(self.inky_display.BLACK)
        self.inky_display.show()

    def draw_inbound_outbound(self, line, stop1, stop2, s1_next_inbound_str, s1_next_outbound_str, s2_next_inbound_str, s2_next_outbound_str):
        """
        Legacy method for backward compatibility.
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

        img = Image.new("P", (self.inky_display.WIDTH, self.inky_display.HEIGHT))
        draw = ImageDraw.Draw(img)
        
        def format_time(time_str):
            if time_str is None:
                return "Later"
            # Parse the ISO format time and convert to local timezone
            dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                # If no timezone info, assume UTC
                dt = dt.replace(tzinfo=timezone.utc)
            # Convert to local time
            local_dt = dt.astimezone()
            return local_dt.strftime("%I:%M%p")
        
        s1_next_inbound = format_time(s1_next_inbound_str)
        s1_next_outbound = format_time(s1_next_outbound_str)
        s2_next_inbound = format_time(s2_next_inbound_str)
        s2_next_outbound = format_time(s2_next_outbound_str)

        font_times = ImageFont.truetype(HankenGroteskMedium, 18)
        font_stop_name = ImageFont.truetype(HankenGroteskBold, 20)
        font_line = ImageFont.truetype(HankenGroteskBold, 24)
        font_date = ImageFont.truetype(HankenGroteskBold, 20)

        #Which line we are displaying information for
        _left_line, _top_line, _right_line, bottom_line = font_line.getbbox(line)
        x_line = self.STANDARD_X_COORD
        y_line = 0
        draw.text((x_line, y_line), line, self.inky_display.BLACK, font_line)

        #Today's date
        today = datetime.now()
        date_text = today.strftime("%m/%d/%y")
        #Get the width of the display
        display_width = self.inky_display.resolution[0]
        length_date = font_stop_name.getlength(date_text)
        x_date = display_width - length_date
        y_date = 0
        draw.text((x_date, y_date), date_text, self.inky_display.RED, font_date)

        #Name of Stop 1
        y_pos = bottom_line #Start below the Line name
        stop1_x = self.STANDARD_X_COORD
        draw.text((stop1_x, y_pos), stop1, self.inky_display.BLACK, font_stop_name)
        _left_stop1, _top_stop1, _right_stop1, bottom_stop1 = font_stop_name.getbbox(stop1)
        y_pos = y_pos + (bottom_stop1)

        #Stop 1 inbound information
        s1_inbound_message = "Next Inbound:    " + s1_next_inbound
        s1_x_inbound = self.STANDARD_X_COORD
        draw.text((s1_x_inbound, y_pos), s1_inbound_message, self.inky_display.BLACK, font_times)
        _left_s1_inbound, _top_s1_inbound, _right_s1_inbound, bottom_s1_inbound = font_stop_name.getbbox(s1_inbound_message)
        y_pos = y_pos + (bottom_s1_inbound)
    
        #Stop 1 outbound information
        s1_outbound_message = "Next Outbound: " + s1_next_outbound
        _s1_x_outbound = self.STANDARD_X_COORD
        #draw.text((s1_x_outbound, y_pos), s1_outbound_message, self.inky_display.BLACK, font_times)
        #left_s1_outbound, top_s1_outbound, right_s1_outbound, bottom_s1_outbound = font_times.getbbox(s1_outbound_message)
        #y_pos = y_pos + (bottom_s1_outbound)

        #Stop 2 name
        stop2_x = self.STANDARD_X_COORD
        draw.text((stop2_x, y_pos), stop2, self.inky_display.BLACK, font_stop_name)
        _left_stop2, _top_stop2, _right_stop2, bottom_stop2 = font_stop_name.getbbox(stop2)
        y_pos = y_pos + (bottom_stop2)

        #Stop 2 inbound information
        s2_inbound_message = "Next Inbound:    " + s2_next_inbound
        s2_x_inbound = self.STANDARD_X_COORD
        draw.text((s2_x_inbound, y_pos), s2_inbound_message, self.inky_display.BLACK, font_times)
        _left_s2_inbound, _top_s2_inbound, _right_s2_inbound, bottom_s2_inbound = font_stop_name.getbbox(s2_inbound_message)
        y_pos = y_pos + (bottom_s2_inbound)
    
        #Stop 2 outbound information
        s2_outbound_message = "Next Outbound: " + s2_next_outbound
        s2_x_outbound = self.STANDARD_X_COORD
        draw.text((s2_x_outbound, y_pos), s2_outbound_message, self.inky_display.BLACK, font_times)
        _left_s2_outbound, _top_s2_outbound, _right_s2_outbound, bottom_s2_outbound = font_times.getbbox(s1_outbound_message)
        y_pos = y_pos + (bottom_s2_outbound)

        self.inky_display.set_image(img)
        self.inky_display.set_border(self.inky_display.BLACK)
        self.inky_display.show()