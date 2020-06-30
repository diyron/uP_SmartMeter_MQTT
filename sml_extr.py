########################################################
# SML extractor
# by André Lange (2020)
# https://github.com/diyron/uP_SmartMeter
########################################################

from binascii import unhexlify

# 9 folgenden Bytes ist die Server ID
# Gerätenummer (9 Bytes) nach dieser Sequenz
obis_srvid_a = "0177070100000009ff010101010b09"   # 1-0:0.0.9   -- variante A
obis_180 = "0177070100010800ff"     # 1-0:1.8.0  # Energiemengen-Register (kWh)
obis_1670 = "0177070100100700ff"    # 1-0:16.7.0 Gesamtleistung in [W] # Wirkleistung (W)
obis_3670 = "0177070100240700ff"    # 1-0:36.7.0 Leistung L1
obis_5670 = "0177070100380700ff"    # 1-0:56.7.0 Leistung L2
obis_7670 = "01770701004c0700ff"    # 1-0:76.7.0 Leistung L3
obis_pubkey = "77078181c78205ff"    # Public Key des Zählers
ident_sc_unit_kWh = "621e52"  # Kennzeichner scaler und Val length /und Einheit-- ab dem 3. folgenden Byte lesen
ident_sc_unit_W = "621b52"


def extract_sml(rawsml: str):

    # device id =================================================
    n = rawsml.find(obis_srvid_a) + len(obis_srvid_a)
    if n != -1:
        devid = rawsml[n + 1]
        #vendor_raw = str(rawsml[n + 2:n + 8])  # ESY# 1s
        vendor_raw = str(unhexlify(rawsml[n + 2:n + 8]))
        devid = devid + vendor_raw[2:5]
        devid = devid + rawsml[n + 8:n + 10]  # 11
        devid = devid + " " + str(int(rawsml[n + 11:n + 18], 16))
        meter_data = {"devid": devid}
    else:
        meter_data = {"devid": "no device id"}

    # values =================================================
    def conv_value(obis, ident):  # convert value from sml notation to string
        nonlocal rawsml
        k = rawsml.find(obis) + len(obis)
        if k != -1:
            k = rawsml.find(ident, k, k + 20) + len(ident)
            scal = int(rawsml[k:k + 2], 16) - 256  # 10^scaler     # das 1. folgende Byte enthalt den scaler
            c = int(rawsml[k + 3], 16) - 1  # Anzahl Bytes des Value (0x59 --> 9 - 1 = 8 Byte) enthält die Byteanzahl
            val = int(rawsml[k + 4:k + 4 + (c * 2)], 16)
            val_h = str(val // (10 ** (scal * -1)))  # value berechnen
            val_l = str(val % (10 ** (scal * -1)))
            return val_h + "." + val_l[:1]
        else:
            return "no value"

    meter_data["1.8.0_Wh"] = conv_value(obis_180, ident_sc_unit_kWh)
    meter_data["16.7.0_W"] = conv_value(obis_1670, ident_sc_unit_W)
    meter_data["36.7.0_W"] = conv_value(obis_3670, ident_sc_unit_W)
    meter_data["56.7.0_W"] = conv_value(obis_5670, ident_sc_unit_W)
    meter_data["76.7.0_W"] = conv_value(obis_7670, ident_sc_unit_W)

    return meter_data

