from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from construct_parser import eepromLayout
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

SETTINGS_MAGIC = 0xD82F  # Magic value for valid settings block

def calculate_settings_checksum(settings_data):
    """Calculate the checksum for the settings block."""
    # Skip the magic value itself in calculation
    data_bytes = settings_data[2:]  # Skip first 2 bytes (magic value)
    
    # Simple additive checksum (adjust algorithm based on actual method used)
    checksum = 0
    for i in range(0, len(data_bytes), 2):
        if i + 1 < len(data_bytes):
            value = (data_bytes[i] << 8) | data_bytes[i + 1]
        else:
            value = data_bytes[i] << 8
        checksum = (checksum + value) & 0xFFFF
    
    return checksum

def validate_eeprom(parsed_data):
    """Validate the EEPROM data using magic values and other checks."""
    validation = {
        'valid': True,
        'messages': []
    }
    
    # Get raw settings data for checksum calculation
    settings_data = parsed_data.settings._io.getvalue()
    calculated_checksum = calculate_settings_checksum(settings_data)
    
    # Check settings block magic against calculated checksum
    if parsed_data.settings.magic != SETTINGS_MAGIC:
        validation['valid'] = False
        validation['messages'].append(
            f"Invalid settings magic value: 0x{parsed_data.settings.magic:04X} "
            f"(expected 0x{SETTINGS_MAGIC:04X}, calculated 0x{calculated_checksum:04X})"
        )
    else:
        validation['messages'].append(
            f"Valid settings magic value: 0x{parsed_data.settings.magic:04X} "
            f"(calculated: 0x{calculated_checksum:04X})"
        )
    
    return validation

def format_group_letters(group_value):
    """Convert a group value into letters A-O.
    Each nibble (4 bits) represents one group number (1-15).
    Returns up to 4 letters representing the groups."""
    letters = []
    for i in range(4):  # 4 nibbles
        # Extract each nibble
        group_num = (group_value >> (i * 4)) & 0xF
        # Convert to letter if valid (1-15 maps to A-O)
        if 1 <= group_num <= 15:
            letters.append(chr(ord('A') + group_num - 1))
    return ','.join(letters)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('display_data', filename=filename))
    return render_template('index.html')

@app.route('/display/<filename>')
def display_data(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        parsed = eepromLayout.parse(data)
        
        # Validate the parsed data
        validation = validate_eeprom(parsed)
        if not validation['valid']:
            for message in validation['messages']:
                flash(message, 'warning')
        
        return render_template('display.html', 
                             parsed=parsed, 
                             validation=validation,
                             format_group_letters=format_group_letters)
    except Exception as e:
        flash(f"Failed to parse file: {e}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 