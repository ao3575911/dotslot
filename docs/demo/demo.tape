# dotslot README demo. Render from repo root: vhs docs/demo/demo.tape
# Then: ffmpeg -i docs/demo.gif -vf "fps=18,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" /tmp/d.gif && gifsicle -O3 --lossy=30 /tmp/d.gif -o docs/demo.gif
Output docs/demo.gif

Set Shell "bash"
Set FontSize 24
Set Width 1200
Set Height 480
Set Padding 20
Set Margin 0
Set Framerate 18
Set TypingSpeed 50ms
Set CursorBlink false
Set Theme { "name": "dotslot", "background": "#1e293b", "foreground": "#e2e8f0", "cursor": "#94a3b8", "selection": "#334155", "black": "#0f172a", "red": "#f87171", "green": "#4ade80", "yellow": "#facc15", "blue": "#60a5fa", "magenta": "#c084fc", "cyan": "#22d3ee", "white": "#e2e8f0", "brightBlack": "#64748b", "brightRed": "#fca5a5", "brightGreen": "#86efac", "brightYellow": "#fde047", "brightBlue": "#93c5fd", "brightMagenta": "#d8b4fe", "brightCyan": "#67e8f9", "brightWhite": "#f8fafc" }

Hide
Type "cd $(mktemp -d) && export PS1='\[\e[38;5;245m\]$\[\e[0m\] ' && printf '# Release v1.0\nOwner:  <./owner:__________>\nStatus: <./status:____________>\n' > release.txt && cp release.txt base.txt && clear"
Enter
Sleep 500ms
Show

Type "cat release.txt"
Sleep 300ms
Enter
Sleep 1s
Type "dotslot scan release.txt"
Sleep 300ms
Enter
Sleep 1s
Type 'dotslot fill release.txt --set owner=Adam --set status="ready to tag" -i'
Sleep 300ms
Enter
Sleep 1s
Type "dotslot check release.txt --base base.txt"
Sleep 300ms
Enter
Sleep 1.5s
Hide
Type "sed -i 's/ready to tag/waiting on legal review/' release.txt && clear"
Enter
Sleep 300ms
Show
Type "cat release.txt   # an agent overflowed the slot"
Sleep 300ms
Enter
Sleep 1s
Type "dotslot check release.txt --base base.txt; echo exit=$?"
Sleep 300ms
Enter
Sleep 2.2s
Hide
Type "clear"
Enter
Sleep 300ms
Show
Sleep 500ms
