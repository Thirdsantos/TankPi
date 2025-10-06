from RPLCD.i2c import CharLCD

# LCD setup (adjust address if needed)
lcd = CharLCD('PCF8574', 0x27, cols=20, rows=4)

# Clear screen
lcd.clear()

# Move cursor to top-left (row 0, col 0) and print text
lcd.cursor_pos = (0, 0)
lcd.write_string("pot")