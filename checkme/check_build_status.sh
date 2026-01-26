#!/bin/bash

# AFASA 2.0 - Build Status Checker
# Quick script to check current build progress without attaching to tmux

echo "🔍 Checking AFASA build status..."
echo ""

# Check if tmux session exists
if ! tmux has-session -t afasa-build 2>/dev/null; then
    echo "❌ No build session found (afasa-build)"
    echo "   Build may have completed or not started yet."
    exit 1
fi

echo "✅ Build session is running!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 LAST 30 LINES OF BUILD OUTPUT:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Capture last 30 lines from tmux session
tmux capture-pane -t afasa-build -p | tail -30

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Tips:"
echo "   • To watch live: ssh -p 2222 meerul@100.88.15.112 -t 'tmux attach -t afasa-build'"
echo "   • To detach safely: Press Ctrl+b then d"
echo "   • To run this again: ./check_build_status.sh"
echo ""

# Check for specific progress indicators
if tmux capture-pane -t afasa-build -p | grep -q "Progress:"; then
    echo "📈 Current Progress:"
    tmux capture-pane -t afasa-build -p | grep "Progress:" | tail -1
    echo ""
fi

# Check which service is building
if tmux capture-pane -t afasa-build -p | grep -q "Building:"; then
    echo "🔨 Current Service:"
    tmux capture-pane -t afasa-build -p | grep "Building:" | tail -1
    echo ""
fi

# Check for downloads
if tmux capture-pane -t afasa-build -p | grep -qE "downloading|Downloading"; then
    echo "⬇️  Active Downloads Detected"
    tmux capture-pane -t afasa-build -p | grep -iE "downloading|download" | tail -5
    echo ""
fi

# Check for errors
if tmux capture-pane -t afasa-build -p | grep -qiE "error|failed"; then
    echo "⚠️  Possible Errors Detected:"
    tmux capture-pane -t afasa-build -p | grep -iE "error|failed" | tail -3
    echo ""
fi

# Check if completed
if tmux capture-pane -t afasa-build -p | grep -q "ALL SERVICES BUILT"; then
    echo "🎉 BUILD COMPLETED SUCCESSFULLY!"
    echo ""
fi
