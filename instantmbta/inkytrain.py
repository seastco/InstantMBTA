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