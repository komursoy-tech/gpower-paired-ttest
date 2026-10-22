import logging
import sys

from .server import mcp


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
