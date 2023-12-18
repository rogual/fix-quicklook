
As of MacOS 11.0 Big Sur, QuickLook now removes the corners from your images before showing them to you.

This is a simple script to find all running QuickLook processes and patch them so they no longer do this.

# Before & After

<svg viewBox="0 0 600 400" width="600" height="400" xmlns="http://www.w3.org/2000/svg">
    <foreignObject width="100%" height="100%">
        <picture>
            <source width="482" height="335" srcset="https://raw.githubusercontent.com/rogual/fix-quicklook/example-images/before-dark.png" media="(prefers-color-scheme: dark)">
            <img width="482" height="335" src="https://raw.githubusercontent.com/rogual/fix-quicklook/example-images/before-light.png">
        </picture>
        <picture>
            <source width="482" height="335" srcset="https://raw.githubusercontent.com/rogual/fix-quicklook/example-images/after-dark.png" media="(prefers-color-scheme: dark)">
            <img width="482" height="335" src="https://raw.githubusercontent.com/rogual/fix-quicklook/example-images/after-light.png">
        </picture>
    </foreignObject>
</svg>


# Requirements

* You must be on an Apple Silicon mac.
* SIP must be disabled.
* LLDB must be installed (it's part of the Xcode command line tools).
* Only tested on Ventura 13.5. Other OS versions may work.

# Usage

`./fix_quicklook.py`

# Room for improvement

This only patches QuickLook for images. Videos, text files etc. are still rounded off. Maybe patch those too.

Maybe add x86 support? I don't have an x86 Mac running an affected OS but would welcome a PR.

Sometimes MacOS spawns new QuickLook processes. Maybe add a daemon that watches for them and patches them as they spawn.

Maybe add a script that adds this as a login item?

It'd be neater to call the script 'fix-quicklook' rather than 'fix_quicklook.py', but it loads itself into LLDB and LLDB requires that the script follows Python module filename conventions. Maybe find a way to get around this.
