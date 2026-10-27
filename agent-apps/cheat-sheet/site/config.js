window.__APP_CONFIG__ = {
  "title": "VS Code, the terminal, and git",
  "platform": "mac",
  "columns": 3,
  "paper": "Letter",
  "theme": "graphite",
  "sections": [
    {
      "label": "Keep forgetting",
      "entries": [
        {
          "action": "Command palette",
          "keys": [
            "mod",
            "shift",
            "p"
          ]
        },
        {
          "action": "Go back to the last spot",
          "platforms": {
            "mac": [
              "ctrl",
              "-"
            ],
            "windows": [
              "alt",
              "left"
            ],
            "linux": [
              "ctrl",
              "alt",
              "-"
            ]
          }
        },
        {
          "action": "Toggle the terminal",
          "keys": [
            "ctrl",
            "`"
          ]
        },
        {
          "action": "Rename a symbol everywhere",
          "keys": [
            "f2"
          ]
        },
        {
          "action": "Undo the last commit, keep the changes",
          "command": "git reset --soft HEAD~1"
        },
        {
          "action": "Zen mode",
          "keys": [
            [
              "mod",
              "k"
            ],
            [
              "z"
            ]
          ],
          "note": "Press Esc twice to leave."
        }
      ]
    },
    {
      "label": "Editing",
      "entries": [
        {
          "action": "Move line up",
          "keys": [
            "alt",
            "up"
          ]
        },
        {
          "action": "Copy line down",
          "keys": [
            "shift",
            "alt",
            "down"
          ],
          "platforms": {
            "linux": [
              "ctrl",
              "shift",
              "alt",
              "down"
            ]
          }
        },
        {
          "action": "Delete line",
          "keys": [
            "mod",
            "shift",
            "k"
          ]
        },
        {
          "action": "Toggle line comment",
          "keys": [
            "mod",
            "/"
          ]
        },
        {
          "action": "Indent line",
          "keys": [
            "mod",
            "]"
          ]
        },
        {
          "action": "Format document",
          "keys": [
            "shift",
            "alt",
            "f"
          ],
          "platforms": {
            "linux": [
              "ctrl",
              "shift",
              "i"
            ]
          }
        }
      ]
    },
    {
      "label": "Multiple cursors",
      "entries": [
        {
          "action": "Add the next match",
          "keys": [
            "mod",
            "d"
          ]
        },
        {
          "action": "Select every match",
          "keys": [
            "mod",
            "shift",
            "l"
          ]
        },
        {
          "action": "Add a cursor above",
          "platforms": {
            "mac": [
              "alt",
              "mod",
              "up"
            ],
            "windows": [
              "ctrl",
              "alt",
              "up"
            ],
            "linux": [
              "shift",
              "alt",
              "up"
            ]
          }
        },
        {
          "action": "A cursor at each line end",
          "keys": [
            "shift",
            "alt",
            "i"
          ]
        },
        {
          "action": "Undo the last cursor",
          "keys": [
            "mod",
            "u"
          ]
        }
      ]
    },
    {
      "label": "Navigate",
      "entries": [
        {
          "action": "Go to file",
          "keys": [
            "mod",
            "p"
          ]
        },
        {
          "action": "Go to line",
          "keys": [
            "ctrl",
            "g"
          ]
        },
        {
          "action": "Go to symbol in file",
          "keys": [
            "mod",
            "shift",
            "o"
          ]
        },
        {
          "action": "Go to definition",
          "keys": [
            "f12"
          ]
        },
        {
          "action": "Peek definition",
          "keys": [
            "alt",
            "f12"
          ],
          "platforms": {
            "linux": [
              "ctrl",
              "shift",
              "f10"
            ]
          }
        },
        {
          "action": "Find in files",
          "keys": [
            "mod",
            "shift",
            "f"
          ]
        },
        {
          "action": "Split the editor",
          "keys": [
            "mod",
            "\\"
          ]
        }
      ]
    },
    {
      "label": "Window",
      "entries": [
        {
          "action": "Toggle the sidebar",
          "keys": [
            "mod",
            "b"
          ]
        },
        {
          "action": "Close the tab",
          "keys": [
            "mod",
            "w"
          ]
        },
        {
          "action": "Reopen a closed tab",
          "keys": [
            "mod",
            "shift",
            "t"
          ]
        },
        {
          "action": "Next tab",
          "keys": [
            "ctrl",
            "tab"
          ]
        },
        {
          "action": "Zoom in",
          "keys": [
            "mod",
            "="
          ]
        }
      ]
    },
    {
      "label": "Terminal",
      "entries": [
        {
          "action": "Search past commands",
          "keys": [
            "ctrl",
            "r"
          ]
        },
        {
          "action": "Clear the screen",
          "keys": [
            "ctrl",
            "l"
          ]
        },
        {
          "action": "Jump to the start of the line",
          "keys": [
            "ctrl",
            "a"
          ]
        },
        {
          "action": "Delete the word before the cursor",
          "keys": [
            "ctrl",
            "w"
          ]
        },
        {
          "action": "Run the last command again",
          "command": "!!"
        },
        {
          "action": "Back to the previous folder",
          "command": "cd -"
        },
        {
          "action": "Last argument of the last command",
          "keys": [
            "alt",
            "."
          ],
          "note": "Or type !$"
        }
      ]
    },
    {
      "label": "tmux",
      "entries": [
        {
          "action": "Split side by side",
          "keys": [
            [
              "ctrl",
              "b"
            ],
            [
              "%"
            ]
          ]
        },
        {
          "action": "Split top and bottom",
          "keys": [
            [
              "ctrl",
              "b"
            ],
            [
              "\""
            ]
          ]
        },
        {
          "action": "Next pane",
          "keys": [
            [
              "ctrl",
              "b"
            ],
            [
              "o"
            ]
          ]
        },
        {
          "action": "Zoom the pane",
          "keys": [
            [
              "ctrl",
              "b"
            ],
            [
              "z"
            ]
          ]
        },
        {
          "action": "Detach",
          "keys": [
            [
              "ctrl",
              "b"
            ],
            [
              "d"
            ]
          ]
        },
        {
          "action": "Attach again",
          "command": "tmux attach"
        }
      ]
    },
    {
      "label": "Git",
      "entries": [
        {
          "action": "Fix the last commit message",
          "command": "git commit --amend"
        },
        {
          "action": "Stash with a name",
          "command": "git stash push -m \"half done\""
        },
        {
          "action": "Branches, newest first",
          "command": "git branch --sort=-committerdate"
        },
        {
          "action": "Throw away a file's changes",
          "command": "git restore <file>"
        },
        {
          "action": "The branch graph",
          "command": "git log --oneline --graph"
        },
        {
          "action": "Who changed this line",
          "command": "git blame -L 40,60 <file>"
        }
      ]
    }
  ]
};
