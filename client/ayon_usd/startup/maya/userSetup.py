"""Initialize AYON USD before the regular AYON Maya startup."""

from pxr import Ar

Ar.SetPreferredResolver("AyonUsdResolver")

print("Preffered USD asset resolver set to `AyonUsdResolver`")
