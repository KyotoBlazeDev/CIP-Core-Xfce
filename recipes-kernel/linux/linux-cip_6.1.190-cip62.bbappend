CIP_XFCE_INTEL_WIFI ?= "0"
SRC_URI:append = "${@bb.utils.contains('CIP_XFCE_INTEL_WIFI', '1', ' file://xfce-intel-wifi.cfg', '', d)}"

CIP_XFCE_I2C_TOUCHPAD ?= "0"
SRC_URI:append = "${@bb.utils.contains('CIP_XFCE_I2C_TOUCHPAD', '1', ' file://xfce-i2c-touchpad.cfg', '', d)}"

CIP_XFCE_VIRTUALBOX ?= "0"
SRC_URI:append = "${@bb.utils.contains('CIP_XFCE_VIRTUALBOX', '1', ' file://xfce-virtualbox.cfg', '', d)}"

CIP_XFCE_INTEL_AUDIO ?= "0"
SRC_URI:append = "${@bb.utils.contains('CIP_XFCE_INTEL_AUDIO', '1', ' file://xfce-intel-audio.cfg', '', d)}"

CIP_XFCE_REMOVABLE_STORAGE ?= "0"
SRC_URI:append = "${@bb.utils.contains('CIP_XFCE_REMOVABLE_STORAGE', '1', ' file://xfce-removable-storage.cfg', '', d)}"

CIP_XFCE_BROAD_GPU ?= "0"
SRC_URI:append = "${@bb.utils.contains('CIP_XFCE_BROAD_GPU', '1', ' file://xfce-broad-gpu.cfg', '', d)}"
PR:append = "${@bb.utils.contains('CIP_XFCE_BROAD_GPU', '1', '+gpu1', '', d)}"

CIP_XFCE_BROAD_WIFI ?= "0"
SRC_URI:append = "${@bb.utils.contains('CIP_XFCE_BROAD_WIFI', '1', ' file://xfce-broad-wifi.cfg', '', d)}"
PR:append = "${@bb.utils.contains('CIP_XFCE_BROAD_WIFI', '1', '+wifi1', '', d)}"
