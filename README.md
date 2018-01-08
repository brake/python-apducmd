ApduCmd
=======
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](https://opensource.org/licenses/MIT) [![GitHub version](https://badge.fury.io/gh/brake%2Fpython-apducmd.svg)](https://badge.fury.io/gh/brake%2Fpython-apducmd)

**SmartCard command shell** (Python) with ability to execute APDU just like commands and view result as status word (SW) and output data on the screen.

Automatically selects first card reader in the system to communicate with, monitors card insertion/removal as well as currently selected EF or DF.

Based on smart card communication library [pyscard](https://github.com/LudovicRousseau/pyscard).
