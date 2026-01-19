"""Command-line interface for PMR-171 CPS"""

import sys
import argparse
from pathlib import Path

from .gui import view_channel_file


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='PMR-171 CPS - Channel Programming Software for PMR-171 radio'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View channel table')
    view_parser.add_argument('file', type=Path, help='JSON file to view')
    
    # Default behavior: Launch GUI
    if len(sys.argv) == 1:
        # Launch GUI with empty channels - user can open files or read from radio
        from .gui import ChannelTableViewer
        viewer = ChannelTableViewer({}, "PMR-171 CPS")
        viewer.show()
        return
    
    # Old-style --view argument (backwards compatibility)
    if sys.argv[1] == '--view':
        json_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        if json_file and json_file.exists():
            view_channel_file(json_file)
        else:
            # Launch GUI without file
            from .gui import ChannelTableViewer
            viewer = ChannelTableViewer({}, "PMR-171 CPS")
            viewer.show()
        return
    
    args = parser.parse_args()
    
    if args.command == 'view':
        view_channel_file(args.file)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
