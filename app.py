from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from construct_parser import eepromLayout
import os
import json
import pprint

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SETTINGS_MAGIC = 0xD82F  # Magic value for valid settings block

def calculate_settings_checksum(settings_data):
    """Calculate the checksum for the settings block."""
    # Skip the magic value itself in calculation
    data_bytes = settings_data[2:]  # Skip first 2 bytes (magic value)
    
    # Simple additive checksum using BIG-Endian byte order
    checksum = 0
    for i in range(0, len(data_bytes), 2):
        if i + 1 < len(data_bytes):
            # BIG-Endian: most significant byte first
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
    
    # Validate power table magic values
    if parsed_data.powerTableVHF.magic != 0x57:
        validation['valid'] = False
        validation['messages'].append(
            f"Invalid VHF power table magic: 0x{parsed_data.powerTableVHF.magic:02X} (expected 0x57)"
        )
    else:
        validation['messages'].append("Valid VHF power table magic: 0x57")
        
    if parsed_data.powerTableUHF.magic != 0xD1:
        validation['valid'] = False
        validation['messages'].append(
            f"Invalid UHF power table magic: 0x{parsed_data.powerTableUHF.magic:02X} (expected 0xD1)"
        )
    else:
        validation['messages'].append("Valid UHF power table magic: 0xD1")
    
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

def serialize_channel(channel):
    """Convert channel data to JSON-serializable format"""
    return {
        'bits': {
            'busyLock': channel.bits.busyLock,
            'reversed': channel.bits.reversed,
            'position': channel.bits.position,
            'pttID': channel.bits.pttID,
            'modulation': channel.bits.modulation,
            'bandwidth': channel.bits.bandwidth
        }
    }

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

@app.route('/display/<filename>', methods=['GET', 'POST'])
def display_data(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        parsed = eepromLayout.parse(data)
        
        # Handle form submission
        if request.method == 'POST':
            if 'channel_info' in request.form:
                # Update all channels
                for i, channel in enumerate(parsed.memoryChannels):
                    channel.bits.busyLock = int(request.form.get(f'busyLock_{i}', '0') == '1')
                    channel.bits.reversed = int(request.form.get(f'reversed_{i}', '0') == '1')
                    channel.bits.position = int(request.form.get(f'position_{i}', '0') == '1')
                    channel.bits.bandwidth = int(request.form.get(f'bandwidth_{i}', '0') == '1')
                
                # Save changes back to file
                modified_data = eepromLayout.build(parsed)
                with open(filepath, "wb") as f:
                    f.write(modified_data)
                flash('All channels updated successfully!', 'success')
        
        # Validate the parsed data
        validation = validate_eeprom(parsed)
        if not validation['valid']:
            for message in validation['messages']:
                flash(message, 'warning')
        
        # Extract power tables for rendering
        vhf_power_table = parsed.powerTableVHF.table
        uhf_power_table = parsed.powerTableUHF.table
        
        # Generate debug data
        debug_data = generate_debug_data(parsed)
        
        return render_template('display.html', 
                             parsed=parsed, 
                             validation=validation,
                             format_group_letters=format_group_letters,
                             vhf_power_table=vhf_power_table,
                             uhf_power_table=uhf_power_table,
                             debug_data=debug_data)
    except Exception as e:
        flash(f"Failed to parse file: {e}")
        return redirect(url_for('index'))

def generate_debug_data(parsed):
    """Generate a formatted string representation of the parsed data for debugging."""
    try:
        # Create a custom dictionary with the parsed data
        debug_dict = {
            'vfoA': format_channel_for_debug(parsed.vfoA),
            'vfoB': format_channel_for_debug(parsed.vfoB),
            'settings': format_settings_for_debug(parsed.settings),
            'powerTableVHF': {
                'magic': parsed.powerTableVHF.magic,
                'table': format_power_table_for_debug(parsed.powerTableVHF.table)
            },
            'powerTableUHF': {
                'magic': parsed.powerTableUHF.magic,
                'table': format_power_table_for_debug(parsed.powerTableUHF.table)
            },
            'bandplanMagic': parsed.bandplanMagic,
            'memoryChannels': format_memory_channels_for_debug(parsed.memoryChannels)
        }
        
        # Format the dictionary as a pretty-printed string
        return pprint.pformat(debug_dict, indent=2, width=100)
    except Exception as e:
        # If anything goes wrong, return the error message
        return f"Error generating debug data: {str(e)}\n\nParsed data type: {type(parsed)}"

def format_power_table_for_debug(power_table):
    """Format a power table for debug display."""
    try:
        # For brevity, just show the first 10 values and a summary
        if len(power_table) > 10:
            sample = [power_table[i] for i in range(10)]
            return f"[{len(power_table)} values] First 10: {sample}"
        else:
            return list(power_table)
    except Exception as e:
        return f"Error formatting power table: {str(e)}"

def format_memory_channels_for_debug(channels):
    """Format memory channels for debug display."""
    try:
        # For brevity, just show the first 3 channels and a summary
        if len(channels) > 3:
            sample = [format_channel_for_debug(channels[i]) for i in range(3)]
            return f"[{len(channels)} channels] First 3: {sample}"
        else:
            return [format_channel_for_debug(channel) for channel in channels]
    except Exception as e:
        return f"Error formatting memory channels: {str(e)}"

def format_channel_for_debug(channel):
    """Format a channel for debug display."""
    try:
        # Try to decode the name as ASCII, but handle errors gracefully
        try:
            name = channel.name.decode('ascii', errors='replace')
        except (AttributeError, UnicodeDecodeError):
            name = str(channel.name)
        
        # Create a dictionary with channel attributes
        channel_dict = {
            'rxFreq': channel.rxFreq,
            'txFreq': channel.txFreq,
            'rxSubTone': channel.rxSubTone,
            'txSubTone': channel.txSubTone,
            'txPower': channel.txPower,
            'name': name
        }
        
        # Add groups if available
        try:
            channel_dict['groups'] = channel.groups.value
        except AttributeError:
            try:
                channel_dict['groups'] = channel.groups
            except AttributeError:
                channel_dict['groups'] = "Unknown"
        
        # Add bits if available
        try:
            channel_dict['bits'] = {
                'busyLock': channel.bits.busyLock,
                'reversed': channel.bits.reversed,
                'position': channel.bits.position,
                'pttID': channel.bits.pttID,
                'modulation': channel.bits.modulation,
                'bandwidth': channel.bits.bandwidth
            }
        except AttributeError:
            channel_dict['bits'] = "Unknown"
        
        return channel_dict
    except Exception as e:
        # If anything goes wrong, return a simplified representation
        return f"Error formatting channel: {str(e)}"

def format_settings_for_debug(settings):
    """Format settings for debug display."""
    # Create a dictionary with all the settings attributes
    # Don't rely on __dict__ as construct objects may not have it
    settings_dict = {
        'magic': settings.magic,
        'squelch': settings.squelch,
        'dualWatch': settings.dualWatch,
        'autoFloor': settings.autoFloor,
        'activeVfo': settings.activeVfo,
        'step': settings.step,
        'rxSplit': settings.rxSplit,
        'txSplit': settings.txSplit,
        'pttMode': settings.pttMode,
        'txModMeter': settings.txModMeter,
        'micGain': settings.micGain,
        'txDeviation': settings.txDeviation,
        'xtal671': settings.xtal671,
        'battStyle': settings.battStyle,
        'scanRange': settings.scanRange,
        'scanPersist': settings.scanPersist,
        'scanResume': settings.scanResume,
        'ultraScan': settings.ultraScan,
        'toneMonitor': settings.toneMonitor,
        'lcdBrightness': settings.lcdBrightness,
        'lcdTimeout': settings.lcdTimeout,
        'breathe': settings.breathe,
        'dtmfDev': settings.dtmfDev,
        'gamma': settings.gamma,
        'repeaterTone': settings.repeaterTone,
        'keyLock': settings.keyLock,
        'bluetooth': settings.bluetooth,
        'powerSave': settings.powerSave,
        'keyTones': settings.keyTones,
        'ste': settings.ste,
        'rfGain': settings.rfGain,
        'sBarStyle': settings.sBarStyle,
        'sqNoiseLev': settings.sqNoiseLev,
        'lastFmtFreq': settings.lastFmtFreq,
        'vox': settings.vox,
        'voxTail': settings.voxTail,
        'txTimeout': settings.txTimeout,
        'dimmer': settings.dimmer,
        'dtmfSpeed': settings.dtmfSpeed,
        'noiseGate': settings.noiseGate,
        'scanUpdate': settings.scanUpdate,
        'asl': settings.asl,
        'disableFmt': settings.disableFmt,
        'pin': settings.pin,
        'pinAction': settings.pinAction,
        'lcdInverted': settings.lcdInverted,
        'afFilters': settings.afFilters,
        'ifFreq': settings.ifFreq,
        'sBarAlwaysOn': settings.sBarAlwaysOn,
        'lockedVfo': settings.lockedVfo,
        'vfoLockActive': settings.vfoLockActive
    }
    
    # Add vfoState if it exists
    try:
        vfo_states = []
        for vfo_state in settings.vfoState:
            vfo_states.append({
                'group': vfo_state.group,
                'lastGroup': vfo_state.lastGroup,
                'mode': vfo_state.mode,
                'groupModeChannels': list(vfo_state.groupModeChannels)
            })
        settings_dict['vfoState'] = vfo_states
    except (AttributeError, IndexError):
        # If vfoState doesn't exist or has a different structure, skip it
        pass
    
    return settings_dict

if __name__ == '__main__':
    app.run(debug=True) 