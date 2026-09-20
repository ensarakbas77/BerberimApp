/* docs/*.md dosyalarını tek bir Word (.docx) belgesinde birleştirir.
 *
 * Kaynak Markdown'dır; Word çıktısı ondan türetilir ve elle düzenlenmez.
 * Kullanım (proje bağımlılıklarından ayrı, geçici bir klasörde):
 *
 *   mkdir /tmp/docx-build && cd /tmp/docx-build && npm init -y && npm install docx marked@12
 *   NODE_PATH=/tmp/docx-build/node_modules node docs/tools/build-docx.js [çıktı.docx]
 *
 * Varsayılan çıktı: docs/dist/Berberim-Dokumantasyon.docx
 * Ortam değişkenleri: DOC_AUTHOR (kapakta görünen ad), DOC_VERSION (ör. commit özeti).
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, AlignmentType, LevelFormat, ImageRun, ExternalHyperlink, Footer, PageNumber, TableOfContents,
} = require("docx");
const { marked } = require("marked");

const DOCS_DIR = path.resolve(__dirname, "..");
const OUT = process.argv[2] || path.join(DOCS_DIR, "dist", "Berberim-Dokumantasyon.docx");
const AUTHOR = process.env.DOC_AUTHOR || "";
const VERSION = process.env.DOC_VERSION || "";

// Birleşik belgedeki sıra: plan, proje raporu, ardından numaralı belgeler.
const ORDER = [
  "README.md",
  "12-proje-raporu.md",
  "01-mimari-genel-bakis.md",
  "02-veri-modeli.md",
  "03-modul-accounts-core-config.md",
  "04-modul-shops.md",
  "05-modul-bookings.md",
  "06-modul-panel.md",
  "07-arayuz-katmani.md",
  "08-test-rehberi.md",
  "09-operasyon.md",
  "10-guvenlik.md",
  "11-kullanici-kilavuzu.md",
];

// A4, 2 cm kenar boşluğu (DXA: 1440 = 1 inç)
const PAGE_W = 11906;
const PAGE_H = 16838;
const MARGIN = 1134;
const CONTENT_W = PAGE_W - 2 * MARGIN;

const COLORS = { ink: "17332A", green: "157A45", line: "BFCDC5", head: "E4EDE7", code: "F2F5F3" };
const BODY_FONT = "Calibri";
const CODE_FONT = "Consolas";

const numberingConfigs = [];
let orderedCounter = 0;

function bulletConfig() {
  const marks = ["•", "◦", "▪"];
  return {
    reference: "bullets",
    levels: [0, 1, 2].map((level) => ({
      level,
      format: LevelFormat.BULLET,
      text: marks[level],
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540 + level * 360, hanging: 270 } } },
    })),
  };
}

function orderedConfig(reference, start) {
  return {
    reference,
    levels: [0, 1, 2].map((level) => ({
      level,
      format: LevelFormat.DECIMAL,
      text: `%${level + 1}.`,
      start: level === 0 ? start : 1,
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540 + level * 360, hanging: 360 } } },
    })),
  };
}

numberingConfigs.push(bulletConfig());

// --- Metin yardımcıları -------------------------------------------------------------------------

/** marked satır içi metni HTML kaçırdığı için (&amp; &lt; ...) geri çevirir. */
function unescapeHtml(text) {
  return text
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&#x27;/g, "'")
    .replace(/&amp;/g, "&");
}

function makeRun(text, style) {
  const value = unescapeHtml(text).replace(/\s*\n\s*/g, " ");
  if (!value) return null;
  const options = { text: value, size: style.size, bold: style.bold, italics: style.italics };
  if (style.code) {
    options.font = CODE_FONT;
    options.size = Math.max(16, (style.size || 22) - 2);
    options.shading = { type: ShadingType.CLEAR, fill: COLORS.code, color: "auto" };
  }
  if (style.link) {
    options.color = COLORS.green;
    options.underline = { type: "single" };
  }
  return new TextRun(options);
}

function plainText(tokens) {
  return (tokens || [])
    .map((token) => (token.tokens && token.tokens.length ? plainText(token.tokens) : token.text || token.raw || ""))
    .join("");
}

function pngSize(buffer) {
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

let currentDocDir = DOCS_DIR;

function imageRun(href, alt, maxWidth, maxHeight) {
  const file = path.resolve(currentDocDir, href);
  const data = fs.readFileSync(file);
  const size = pngSize(data);
  const scale = Math.min(1, maxWidth / size.width, maxHeight / size.height);
  return new ImageRun({
    type: "png",
    data,
    transformation: { width: Math.round(size.width * scale), height: Math.round(size.height * scale) },
    altText: { title: alt || path.basename(file), description: alt || path.basename(file), name: path.basename(file) },
  });
}

/** Satır içi jetonları TextRun / ExternalHyperlink dizisine çevirir. */
function inlineRuns(tokens, style = {}) {
  const out = [];
  for (const token of tokens || []) {
    switch (token.type) {
      case "text":
      case "escape":
        if (token.tokens && token.tokens.length) out.push(...inlineRuns(token.tokens, style));
        else {
          const run = makeRun(token.text, style);
          if (run) out.push(run);
        }
        break;
      case "strong":
        out.push(...inlineRuns(token.tokens, { ...style, bold: true }));
        break;
      case "em":
        out.push(...inlineRuns(token.tokens, { ...style, italics: true }));
        break;
      case "codespan": {
        const run = makeRun(token.text, { ...style, code: true });
        if (run) out.push(run);
        break;
      }
      case "br":
        out.push(new TextRun({ break: 1 }));
        break;
      case "link":
        if (/^https?:\/\//.test(token.href)) {
          out.push(
            new ExternalHyperlink({ link: token.href, children: inlineRuns(token.tokens, { ...style, link: true }) })
          );
        } else {
          // Belgeler arası bağlantılar Word'de düz metin olarak kalır (bölümler zaten içindekiler tablosundadır).
          out.push(...inlineRuns(token.tokens, style));
        }
        break;
      case "image":
        out.push(imageRun(token.href, token.text, 560, 700));
        break;
      case "html": {
        const run = makeRun(token.text || token.raw, style);
        if (run) out.push(run);
        break;
      }
      default:
        if (token.raw) {
          const run = makeRun(token.raw, style);
          if (run) out.push(run);
        }
    }
  }
  return out;
}

// --- Blok dönüşümleri ---------------------------------------------------------------------------

function distributeWidths(weights, total, minimum) {
  const sum = weights.reduce((a, b) => a + b, 0);
  let widths = weights.map((w) => Math.max(minimum, Math.floor((w / sum) * total)));
  let diff = total - widths.reduce((a, b) => a + b, 0);
  // Yuvarlama ya da alt sınır farkını en geniş sütuna yansıt
  const widest = widths.indexOf(Math.max(...widths));
  widths[widest] += diff;
  return widths;
}

function buildTable(token) {
  const header = token.header.map((cell) => cell.tokens);
  const rows = token.rows.map((row) => row.map((cell) => cell.tokens));
  const columns = header.length;
  const weights = [];
  for (let i = 0; i < columns; i += 1) {
    const lengths = [plainText(header[i]).length, ...rows.map((row) => Math.min(plainText(row[i]).length, 70))];
    weights.push(Math.min(70, Math.max(8, Math.max(...lengths))));
  }
  const widths = distributeWidths(weights, CONTENT_W, 900);
  const border = { style: BorderStyle.SINGLE, size: 4, color: COLORS.line };
  const borders = { top: border, bottom: border, left: border, right: border };

  const makeCell = (tokens, width, isHeader) =>
    new TableCell({
      width: { size: width, type: WidthType.DXA },
      borders,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      shading: isHeader ? { type: ShadingType.CLEAR, fill: COLORS.head, color: "auto" } : undefined,
      children: [
        new Paragraph({
          spacing: { after: 0 },
          children: inlineRuns(tokens, { size: 18, bold: isHeader }),
        }),
      ],
    });

  const tableRows = [
    new TableRow({
      tableHeader: true,
      cantSplit: true,
      children: header.map((cell, i) => makeCell(cell, widths[i], true)),
    }),
    ...rows.map(
      (row) =>
        new TableRow({ cantSplit: true, children: row.map((cell, i) => makeCell(cell, widths[i], false)) })
    ),
  ];
  return [
    new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths, rows: tableRows }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}

function buildList(token, level, ctx) {
  const out = [];
  let reference = "bullets";
  if (token.ordered) {
    orderedCounter += 1;
    reference = `ordered-${orderedCounter}`;
    numberingConfigs.push(orderedConfig(reference, Number(token.start) || 1));
  }
  const clamp = Math.min(level, 2);
  for (const item of token.items) {
    let first = true;
    for (const child of item.tokens) {
      if (child.type === "text" || child.type === "paragraph") {
        out.push(
          new Paragraph({
            numbering: { reference, level: clamp },
            spacing: { after: 60 },
            children: inlineRuns(child.tokens, { size: ctx.size }),
          })
        );
      } else if (child.type === "list") {
        out.push(...buildList(child, level + 1, ctx));
      } else {
        out.push(...buildBlocks([child], ctx));
      }
      first = false;
    }
    if (first) out.push(new Paragraph({ numbering: { reference, level: clamp }, children: [] }));
  }
  return out;
}

function headingLevelFor(depth) {
  return [null, HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3, HeadingLevel.HEADING_4][
    Math.min(depth, 4)
  ];
}

function buildBlocks(tokens, ctx = { size: 22 }) {
  const out = [];
  for (const token of tokens) {
    switch (token.type) {
      case "heading": {
        let depth = token.depth;
        if (ctx.shift && ctx.seenFirstH1 && depth <= 4) depth += 1;
        const isChapter = token.depth === 1 && !ctx.seenFirstH1;
        if (token.depth === 1) ctx.seenFirstH1 = true;
        out.push(
          new Paragraph({
            heading: headingLevelFor(isChapter ? 1 : depth),
            pageBreakBefore: isChapter,
            keepNext: true,
            children: inlineRuns(token.tokens, { size: undefined }).map((run) => run),
          })
        );
        break;
      }
      case "paragraph": {
        const onlyImage = token.tokens.length === 1 && token.tokens[0].type === "image";
        if (onlyImage) {
          out.push(
            new Paragraph({
              alignment: AlignmentType.CENTER,
              keepNext: true,
              spacing: { before: 120, after: 40 },
              children: inlineRuns(token.tokens),
            })
          );
          out.push(
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 200 },
              children: [new TextRun({ text: token.tokens[0].text, italics: true, size: 18, color: "4E5F58" })],
            })
          );
        } else {
          const extra = ctx.quote
            ? {
                indent: { left: 360 },
                border: { left: { style: BorderStyle.SINGLE, size: 12, color: COLORS.green, space: 8 } },
              }
            : {};
          out.push(
            new Paragraph({ spacing: { after: 120 }, ...extra, children: inlineRuns(token.tokens, { size: ctx.size }) })
          );
        }
        break;
      }
      case "list":
        out.push(...buildList(token, 0, ctx));
        out.push(new Paragraph({ spacing: { after: 60 }, children: [] }));
        break;
      case "table":
        out.push(...buildTable(token));
        break;
      case "code": {
        const lines = token.text.replace(/\t/g, "    ").split("\n");
        lines.forEach((line, index) => {
          out.push(
            new Paragraph({
              spacing: { before: 0, after: 0, line: 240 },
              indent: { left: 120 },
              keepLines: true,
              keepNext: index < lines.length - 1,
              shading: { type: ShadingType.CLEAR, fill: COLORS.code, color: "auto" },
              border: { left: { style: BorderStyle.SINGLE, size: 12, color: COLORS.green, space: 6 } },
              children: [new TextRun({ text: line.length ? line : " ", font: CODE_FONT, size: 16 })],
            })
          );
        });
        out.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
        break;
      }
      case "blockquote":
        out.push(...buildBlocks(token.tokens, { ...ctx, quote: true }));
        break;
      case "hr":
        out.push(
          new Paragraph({
            spacing: { before: 120, after: 120 },
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLORS.line, space: 1 } },
            children: [],
          })
        );
        break;
      default:
        break; // space, html vb.
    }
  }
  return out;
}

// --- Belgeyi kur --------------------------------------------------------------------------------

function loadDocument(file) {
  currentDocDir = path.dirname(path.join(DOCS_DIR, file));
  const source = fs.readFileSync(path.join(DOCS_DIR, file), "utf8");
  const tokens = marked.lexer(source);
  const h1Count = tokens.filter((t) => t.type === "heading" && t.depth === 1).length;
  // Birden fazla 1. düzey başlığı olan belgede ilk başlık bölüm başlığıdır, sonrakiler bir düzey aşağı iner.
  const ctx = { size: 22, shift: h1Count > 1, seenFirstH1: false };
  return buildBlocks(tokens, ctx);
}

const chapters = ORDER.flatMap((file) => loadDocument(file));

const cover = [
  new Paragraph({ spacing: { before: 3200, after: 200 }, children: [new TextRun({ text: "Berberim", bold: true, size: 84, color: COLORS.ink, font: BODY_FONT })] }),
  new Paragraph({ spacing: { after: 400 }, children: [new TextRun({ text: "Kod ve Sistem Dokümantasyonu", size: 40, color: COLORS.green })] }),
  new Paragraph({
    spacing: { after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: COLORS.green, space: 6 } },
    children: [],
  }),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "Karamürsel'deki berberler için online randevu uygulaması", size: 26 })] }),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "Canlı adres: https://berberimapp.vercel.app", size: 22 })] }),
  new Paragraph({
    spacing: { before: 1600, after: 60 },
    children: [new TextRun({ text: "Udemy: AI Destekli Yazılım Geliştirme (Atıl Samancıoğlu)", size: 22 })],
  }),
  ...(AUTHOR
    ? [new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: `Hazırlayan: ${AUTHOR}`, size: 22 })] })]
    : []),
  new Paragraph({
    spacing: { after: 60 },
    children: [new TextRun({ text: `Eylül 2026${VERSION ? `  |  sürüm ${VERSION}` : ""}`, size: 22 })],
  }),
];

const tocSection = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "İçindekiler" })] }),
  new TableOfContents("İçindekiler", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({
    spacing: { before: 200 },
    children: [
      new TextRun({
        text: "Word içindekiler tablosunu ilk açılışta güncellemek isteyebilir; \"Evet\" deyin ya da tabloya sağ tıklayıp \"Alanı güncelleştir\" seçin.",
        italics: true,
        size: 18,
        color: "4E5F58",
      }),
    ],
  }),
];

const heading = (id, name, size, before, after) => ({
  id,
  name,
  basedOn: "Normal",
  next: "Normal",
  quickFormat: true,
  run: { size, bold: true, font: BODY_FONT, color: COLORS.ink },
  paragraph: { spacing: { before, after }, outlineLevel: Number(id.slice(-1)) - 1 },
});

const footer = new Footer({
  children: [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "4E5F58" })],
    }),
  ],
});

const document = new Document({
  creator: AUTHOR || "Berberim",
  title: "Berberim: Kod ve Sistem Dokümantasyonu",
  description: "Berberim kod tabanını anlamak için mimari, modül kılavuzları, test, operasyon ve güvenlik belgeleri",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: BODY_FONT, size: 22 }, paragraph: { spacing: { line: 276 } } } },
    paragraphStyles: [
      heading("Heading1", "Heading 1", 40, 0, 240),
      heading("Heading2", "Heading 2", 30, 320, 140),
      heading("Heading3", "Heading 3", 26, 240, 100),
      heading("Heading4", "Heading 4", 23, 200, 80),
    ],
  },
  numbering: { config: numberingConfigs },
  sections: [
    {
      properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
      children: cover,
    },
    {
      properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
      footers: { default: footer },
      children: [...tocSection, ...chapters],
    },
  ],
});

Packer.toBuffer(document).then((buffer) => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, buffer);
  console.log(`Yazıldı: ${OUT} (${(buffer.length / 1024).toFixed(0)} KB, ${ORDER.length} belge)`);
});
