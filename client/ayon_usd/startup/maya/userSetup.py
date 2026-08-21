"""Initialize AYON USD before the regular AYON Maya startup."""

from pxr import Ar

Ar.SetPreferredResolver("AyonUsdResolver")

print("Preferred USD asset resolver set to 'AyonUsdResolver'")
