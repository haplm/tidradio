#!/usr/bin/env python3

from construct import (
    Struct, Int8ul, Int16ul, Int32ul,
    Bytes, Array, Padding, PaddedString,
    BitStruct, BitsInteger, Flag, Union,
    this
)
from pprint import pprint


#
# Helpers
#
def bits_channelinfo():
    """
    struct {
        u8 busyLock   : 1;
        u8 reversed   : 1;
        u8 position   : 1;
        u8 pttID      : 2;
        u8 modulation : 2;
        u8 bandwidth  : 1;
    } bits;
    """
    return BitStruct(
        "busyLock" / BitsInteger(1),
        "reversed" / BitsInteger(1),
        "pttID" / BitsInteger(2),
        "position" / BitsInteger(1),
        "modulation" / BitsInteger(2),
        "bandwidth" / BitsInteger(1),
    )


#
# Individual Structures
#

# bandPlan
bandPlan = Struct(
    "startFreq" / Int32ul,     # u32, little-endian
    "endFreq"   / Int32ul,     # u32, little-endian
    "maxPower"  / Int8ul,      # u8
    "bits" / BitStruct(        # 1 byte of bitfields
        "bandwidth"   / BitsInteger(3),
        "modulation"  / BitsInteger(3),
        "wrap"        / Flag,  # 1 bit
        "txAllowed"   / Flag,  # 1 bit
    )
)

# dtmfSequence
dtmfSequence = Struct(
    "first" / BitStruct(
        "d6"     / BitsInteger(4),
        "d5"     / BitsInteger(4),
        "d4"     / BitsInteger(4),
        "d3"     / BitsInteger(4),
        "d2"     / BitsInteger(4),
        "d1"     / BitsInteger(4),
        "d0"     / BitsInteger(4),
        "length" / BitsInteger(4),
    ),
    "second" / BitStruct(
        "d8" / BitsInteger(4),
        "d7" / BitsInteger(4),
    )
)

# scanPreset
scanPreset = Struct(
    "startFreq" / Int32ul,     # U32
    "range"     / Int16ul,     # u16
    "step"      / Int16ul,     # u16
    "resume"    / Int8ul,      # u8
    "persist"   / Int8ul,      # u8
    "bits" / BitStruct(
        "ultrascan"  / BitsInteger(6),
        "modulation" / BitsInteger(2),
    ),
    "label" / Bytes(9)
)

# channelInfo
channelInfo = Struct(
    "rxFreq" / Int32ul,
    "txFreq" / Int32ul,
    "rxSubTone" / Int16ul,
    "txSubTone" / Int16ul,
    "txPower" / Int8ul,

    # groups union: either raw value or bitfields
    "groups" / Union(0,
        "value" / Int16ul,
        "single" / BitStruct(
            "g0" / BitsInteger(4),
            "g1" / BitsInteger(4),
            "g2" / BitsInteger(4),
            "g3" / BitsInteger(4),
        )
    ),

    "bits" / bits_channelinfo(),

    "reserved" / Bytes(4),

    "name" / Bytes(12)
)

# Manually calculate the size of channelInfo
channelInfo_size = (
    4 +  # rxFreq
    4 +  # txFreq
    2 +  # rxSubTone
    2 +  # txSubTone
    1 +  # txPower
    2 +  # groups (Union, assume max size of Int16ul)
    1 +  # bits (BitStruct, 1 byte)
    4 +  # reserved
    12   # name (Bytes(12))
)

# settingsBlock
settingsBlock = Struct(
    "magic"         / Int16ul,   # 0x00
    "squelch"       / Int8ul,    # 0x02
    "dualWatch"     / Int8ul,    # 0x03
    "autoFloor"     / Int8ul,    # 0x04
    "activeVfo"     / Int8ul,    # 0x05
    "step"          / Int16ul,   # 0x06
    "rxSplit"       / Int16ul,   # 0x08
    "txSplit"       / Int16ul,   # 0x0a
    "pttMode"       / Int8ul,    # 0x0c
    "txModMeter"    / Int8ul,    # 0x0d
    "micGain"       / Int8ul,    # 0x0e
    "txDeviation"   / Int8ul,    # 0x0f
    "xtal671"       / Int8ul,    # 0x10 (signed)
    "battStyle"     / Int8ul,    # 0x11
    "scanRange"     / Int16ul,   # 0x12
    "scanPersist"   / Int16ul,   # 0x14
    "scanResume"    / Int8ul,    # 0x16
    "ultraScan"     / Int8ul,    # 0x17
    "toneMonitor"   / Int8ul,    # 0x18
    "lcdBrightness" / Int8ul,    # 0x19
    "lcdTimeout"    / Int8ul,    # 0x1a
    "breathe"       / Int8ul,    # 0x1b
    "dtmfDev"       / Int8ul,    # 0x1c
    "gamma"         / Int8ul,    # 0x1d
    "repeaterTone"  / Int16ul,   # 0x1e

    # vfoState[2]
    "vfoState" / Array(2, Struct(
        "group" / Int8ul,
        "lastGroup" / Int8ul,
        "groupModeChannels" / Array(16, Int8ul),
        "mode" / Int8ul,
    )),

    "keyLock"       / Int8ul,    # 0x46
    "bluetooth"     / Int8ul,    # 0x47
    "powerSave"     / Int8ul,    # 0x48
    "keyTones"      / Int8ul,    # 0x49
    "ste"           / Int8ul,    # 0x4a
    "rfGain"        / Int8ul,    # 0x4b
    "sBarStyle"     / Int8ul,    # 0x4c
    "sqNoiseLev"    / Int8ul,    # 0x4d
    "lastFmtFreq"   / Int32ul,   # 0x4e
    "vox"           / Int8ul,    # 0x52
    "voxTail"       / Int16ul,   # 0x53
    "txTimeout"     / Int8ul,    # 0x55
    "dimmer"        / Int8ul,    # 0x56
    "dtmfSpeed"     / Int8ul,    # 0x57
    "noiseGate"     / Int8ul,    # 0x58
    "scanUpdate"    / Int8ul,    # 0x59
    "asl"           / Int8ul,    # 0x5a
    "disableFmt"    / Int8ul,    # 0x5b
    "pin"           / Int16ul,   # 0x5c
    "pinAction"     / Int8ul,    # 0x5e
    "lcdInverted"   / Int8ul,    # 0x5f
    "afFilters"     / Int8ul,    # 0x60
    "ifFreq"        / Int8ul,    # 0x61
    "sBarAlwaysOn"  / Int8ul,    # 0x62
    "lockedVfo"     / Int8ul,    # 0x63
    "vfoLockActive" / Int8ul,    # 0x64

    "filler"        / Bytes(27)
)

#
# Full EEPROM layout with corrected padding
#
eepromLayout = Struct(
    # 0x0000
    "vfoA" / channelInfo,
    # 0x0020
    "vfoB" / channelInfo,
    # 0x0040
    "memoryChannels" / Array(198, channelInfo),
    # 0x1900 => settingsBlock
    "settings" / settingsBlock,
    # Corrected padding to 0x1A00
    Padding(0x1A00 - (0x1980)),
    "bandplanMagic" / Int16ul,       # 0x1A00
    "bandPlans" / Array(20, bandPlan),
    # Jump to 0x1B00
    Padding(0x1B00 - (0x1A00 + 2 + 20 * bandPlan.sizeof())),
    "scanPresets" / Array(20, scanPreset),
    # Jump to 0x1C90
    Padding(0x1C90 - (0x1B00 + 20 * scanPreset.sizeof())),
    "groupLabels" / Array(16, Bytes(6)),
    # Jump to 0x1CF0
    Padding(0x1CF0 - (0x1C90 + 16 * 6)),
    "dtmfPresets" / Array(20, Struct(
        "sequence" / dtmfSequence,
        "sequenceLabel" / Bytes(8)
    )),
    # Jump to 0x1DFC
    Padding(0x1DFC - (0x1CF0 + 20 * (dtmfSequence.sizeof() + 8))),
    "maxPowerWattsUHF" / Int8ul,
    "maxPowerSettingUHF" / Int8ul,
    "maxPowerWattsVHF" / Int8ul,
    "maxPowerSettingVHF" / Int8ul,
    "powerTableVHF" / Array(256, Int8ul),
    "powerTableUHF" / Array(256, Int8ul),
    # Finally consume up to 0x2000 if needed
    Padding(0x2000 - (0x1DFC + 4 + 256 * 2))
)


if __name__ == "__main__":
    # Adjust the filename as appropriate for your situation
    with open("codeplug.nfw", "rb") as f:
        data = f.read()

    # Parse the EEPROM data
    parsed = eepromLayout.parse(data)

    # Print all parsed fields
    print("Parsed EEPROM Layout:")
    pprint(parsed)