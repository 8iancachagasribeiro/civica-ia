"""Generate simple, original app icons in PNG using Python stdlib only."""
from __future__ import annotations
import math
import struct
import zlib
from pathlib import Path

def png_icon(size: int) -> bytes:
    if size not in (192,512):
        raise ValueError("Unsupported icon dimension")
    lines=[]
    for y in range(size):
        row=bytearray([0])  # PNG filter none.
        for x in range(size):
            X=(x+0.5)/size
            Y=(y+0.5)/size
            radius=0.21
            cx=max(radius,min(1-radius,X))
            cy=max(radius,min(1-radius,Y))
            inside=(X-cx)**2+(Y-cy)**2 <= radius**2
            if not inside:
                rgba=(0,0,0,0)
            else:
                dx=X-0.5;dy=Y-0.5
                circle=(dx*dx+dy*dy)<=0.31**2
                ink=(25,44,44,255)
                mint=(177,233,210,255)
                rgba=mint if circle else ink
                if circle:
                    line=min(abs(dx),abs(dy),abs(dx-dy)/math.sqrt(2),abs(dx+dy)/math.sqrt(2))
                    if (line<=0.021 and math.hypot(dx,dy)<0.24) or math.hypot(dx,dy)<0.053:
                        rgba=ink
            row.extend(rgba)
        lines.append(bytes(row))
    def chunk(kind,payload):
        return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",zlib.crc32(kind+payload)&0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"
            +chunk(b"IHDR",struct.pack(">IIBBBBB",size,size,8,6,0,0,0))
            +chunk(b"IDAT",zlib.compress(b"".join(lines),9))
            +chunk(b"IEND",b""))

def main():
    folder=Path("app/static")
    folder.mkdir(parents=True,exist_ok=True)
    for size in (192,512):
        path=folder/f"icon-{size}.png"
        path.write_bytes(png_icon(size))
        print(f"Generated {path}: {path.stat().st_size} bytes")

if __name__=="__main__":
    main()
