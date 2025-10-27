import struct
import zlib
from PIL import Image, ExifTags, JpegImagePlugin, PngImagePlugin

# ========= Utilidades comuns =========

def _safe_print_dict(d, max_value_len=200):
    for k, v in d.items():
        vs = str(v)
        if len(vs) > max_value_len:
            vs = vs[:max_value_len] + f"... [len={len(vs)}]"
        print(f"  - {k}: {vs}")

def _extract_xmp_from_bytes(data: bytes):
    """
    Procura um pacote XMP (XML) dentro de bytes.
    Funciona tanto para JPEG (APP1) quanto para PNG (iTXt) se o XML estiver íntegro.
    """
    start = data.find(b"<x:xmpmeta")
    if start == -1:
        start = data.find(b"<xmpmeta")
    if start == -1:
        return None
    end = data.find(b"</x:xmpmeta>")
    if end == -1:
        end = data.find(b"</xmpmeta>")
    if end == -1:
        return None
    xml = data[start:end] + (b"</x:xmpmeta>" if b"</x:xmpmeta>" in data else b"</xmpmeta>")
    try:
        return xml.decode("utf-8", errors="replace")
    except Exception:
        return xml.decode("latin-1", errors="replace")

# ========= PNG =========

def list_png_chunks(path):
    """
    Itera e lista todos os chunks do PNG, retornando (type, length, offset).
    Também decodifica tEXt/zTXt/iTXt (texto) quando possível.
    """
    chunks = []
    texts = []
    xmp_xml = None
    exif_bytes = None

    with open(path, "rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Arquivo não parece ser PNG válido.")

        while True:
            len_bytes = f.read(4)
            if len(len_bytes) < 4:
                break
            length = struct.unpack(">I", len_bytes)[0]
            ctype = f.read(4)
            if len(ctype) < 4:
                break
            cdata = f.read(length)
            crc = f.read(4)
            ctype_str = ctype.decode("ascii", errors="replace")
            offset = f.tell() - (length + 12)  # posição do início do chunk
            chunks.append((ctype_str, length, offset))

            # Textual data
            if ctype_str == "tEXt":
                # key\0value
                if b"\x00" in cdata:
                    k, v = cdata.split(b"\x00", 1)
                    texts.append((ctype_str, k.decode("latin-1"), v.decode("latin-1", errors="replace")))
            elif ctype_str == "zTXt":
                # key\0comp_flag\comp_method\compressed_text
                try:
                    parts = cdata.split(b"\x00", 1)
                    key = parts[0].decode("latin-1")
                    rest = parts[1]
                    comp_flag = rest[0]
                    comp_method = rest[1]
                    comp_data = rest[2:]
                    if comp_flag == 0 and comp_method == 0:  # zlib/deflate
                        txt = zlib.decompress(comp_data).decode("latin-1", errors="replace")
                        texts.append((ctype_str, key, txt))
                except Exception:
                    pass
            elif ctype_str == "iTXt":
                # key\0comp_flag\comp_method\lang\0\x00translated\0\x00text
                try:
                    # Split at first \0 for key
                    nul1 = cdata.find(b"\x00")
                    key = cdata[:nul1].decode("latin-1")
                    rest = cdata[nul1+1:]
                    comp_flag = rest[0]
                    comp_method = rest[1]
                    # lang (null-terminated)
                    rest = rest[2:]
                    nul2 = rest.find(b"\x00")
                    lang = rest[:nul2].decode("utf-8", errors="replace")
                    rest = rest[nul2+1:]
                    # translated keyword (null-terminated)
                    nul3 = rest.find(b"\x00")
                    translated = rest[:nul3].decode("utf-8", errors="replace")
                    text_bytes = rest[nul3+1:]
                    if comp_flag == 1 and comp_method == 0:
                        text = zlib.decompress(text_bytes).decode("utf-8", errors="replace")
                    else:
                        text = text_bytes.decode("utf-8", errors="replace")
                    texts.append((ctype_str, key, text, lang, translated))

                    # Heurística: XMP costuma vir como iTXt com chave tipo 'XML:com.adobe.xmp'
                    if "xmp" in key.lower() or ("xml" in key.lower()):
                        maybe = _extract_xmp_from_bytes(text.encode("utf-8", errors="replace"))
                        if maybe:
                            xmp_xml = maybe
                except Exception:
                    pass
            elif ctype_str == "eXIf":
                # EXIF em PNG (conteúdo estilo TIFF). Guardamos bytes para tentar decodificar.
                exif_bytes = cdata

    return chunks, texts, xmp_xml, exif_bytes

def inspect_png(path):
    print(f"=== PNG: {path} ===")
    img = Image.open(path)
    print("Básico:", {"format": img.format, "size": img.size, "mode": img.mode})
    if img.info:
        print("Pillow img.info:")
        _safe_print_dict(img.info)

    # Chunks + textos
    chunks, texts, xmp_xml, exif_bytes = list_png_chunks(path)
    print("\nChunks (ordem no arquivo):")
    for t, L, off in chunks:
        print(f"  - {t} (len={L}, offset={off})")

    if texts:
        print("\nTextos embutidos (tEXt/zTXt/iTXt):")
        for entry in texts:
            tag = entry[0]
            if tag in ("tEXt", "zTXt"):
                _, k, v = entry
                print(f"  [{tag}] {k} = {v[:200]}{'...' if len(v)>200 else ''}")
            else:
                _, k, v, lang, tr = entry
                print(f"  [iTXt] key={k}, lang='{lang}', translated='{tr}'")
                print(f"         text={v[:200]}{'...' if len(v)>200 else ''}")

    if xmp_xml:
        print("\nXMP detectado (trecho):")
        print(xmp_xml[:500] + ("..." if len(xmp_xml) > 500 else ""))

    # ICC profile (via Pillow)
    icc = img.info.get("icc_profile")
    if icc:
        print(f"\nICC profile: {len(icc)} bytes")

    # EXIF em PNG (eXIf)
    if exif_bytes:
        print(f"\nEXIF (eXIf) presente no PNG: {len(exif_bytes)} bytes")
        try:
            import exifread  # opcional
            # exifread espera um arquivo; truque: criar um buffer com cabeçalho TIFF é suficiente
            # Muitos leitores aceitam bytes diretos:
            tags = exifread.process_file(
                # Simula arquivo usando BytesIO
                __import__("io").BytesIO(exif_bytes),
                details=False
            )
            print("  Tags EXIF (via exifread):")
            for k, v in list(tags.items())[:50]:
                print(f"   - {k}: {v}")
        except ImportError:
            print("  (Instale 'exifread' para decodificar tags EXIF do chunk eXIf.)")

# ========= JPEG =========

def _decode_exif_with_pillow(img):
    exif = img.getexif()
    if not exif:
        return {}
    tagmap = {ExifTags.TAGS.get(k, k): exif.get(k) for k in exif.keys()}
    return tagmap

def _extract_gps_from_exif(tagmap):
    gps = tagmap.get("GPSInfo")
    if not gps:
        return None
    # Pillow pode trazer GPSInfo como dict com sub-tags numéricas
    gpstags = {ExifTags.GPSTAGS.get(k, k): gps[k] for k in gps.keys()}
    def _to_deg(rational):
        # Rational -> float degrees
        try:
            d, m, s = rational
            d = d[0]/d[1] if isinstance(d, tuple) else float(d)
            m = m[0]/m[1] if isinstance(m, tuple) else float(m)
            s = s[0]/s[1] if isinstance(s, tuple) else float(s)
            return d + m/60 + s/3600
        except Exception:
            return None

    lat = None
    lon = None
    if "GPSLatitude" in gpstags and "GPSLatitudeRef" in gpstags:
        lat = _to_deg(gpstags["GPSLatitude"])
        if gpstags["GPSLatitudeRef"] in ("S", b"S"):
            lat = -lat if lat is not None else None
    if "GPSLongitude" in gpstags and "GPSLongitudeRef" in gpstags:
        lon = _to_deg(gpstags["GPSLongitude"])
        if gpstags["GPSLongitudeRef"] in ("W", b"W"):
            lon = -lon if lon is not None else None
    return {"lat": lat, "lon": lon, **gpstags}

def _extract_xmp_from_jpeg(path):
    # Lê APP1/APP13 e tenta achar XMP XML
    with open(path, "rb") as f:
        data = f.read()
    return _extract_xmp_from_bytes(data)

def _extract_iptc_with_pillow(img):
    try:
        info = JpegImagePlugin.getiptcinfo(img)
        if not info:
            return None
        # Chaves IPTC são pares (record, dataset). Ex.: (2, 5) = ObjectName, (2, 120) = Caption
        # Convertendo para strings simples quando possível:
        decoded = {}
        for k, v in info.items():
            key = f"{k}"
            try:
                if isinstance(v, bytes):
                    v = v.decode("utf-8", errors="replace")
                elif isinstance(v, (list, tuple)):
                    v = [x.decode("utf-8", errors="replace") if isinstance(x, bytes) else x for x in v]
            except Exception:
                pass
            decoded[key] = v
        return decoded
    except Exception:
        return None

def inspect_jpeg(path):
    print(f"=== JPEG: {path} ===")
    img = Image.open(path)
    print("Básico:", {"format": img.format, "size": img.size, "mode": img.mode})

    # EXIF (Pillow)
    exif_tags = _decode_exif_with_pillow(img)
    if exif_tags:
        print("\nEXIF (Pillow):")
        _safe_print_dict(exif_tags)

        gps = _extract_gps_from_exif(exif_tags)
        if gps:
            print("\nGPS (derivado do EXIF):")
            _safe_print_dict(gps)

    # IPTC (APP13 / 8BIM)
    iptc = _extract_iptc_with_pillow(img)
    if iptc:
        print("\nIPTC (APP13/8BIM):")
        _safe_print_dict(iptc)

    # XMP
    xmp = _extract_xmp_from_jpeg(path)
    if xmp:
        print("\nXMP detectado (trecho):")
        print(xmp[:500] + ("..." if len(xmp) > 500 else ""))

    # ICC profile
    icc = img.info.get("icc_profile")
    if icc:
        print(f"\nICC profile: {len(icc)} bytes")

# ========= Exemplo de uso =========
if __name__ == "__main__":
    # Troque pelos seus caminhos de teste:
    png_path = "data/example.png"
    jpg_path = "data/hector.jpg"

    try:
        inspect_png(png_path)
    except Exception as e:
        print(f"[PNG] Erro: {e}")

    print("\n" + "="*80 + "\n")

    try:
        inspect_jpeg(jpg_path)
    except Exception as e:
        print(f"[JPEG] Erro: {e}")
