-- Pandoc Lua filter for the Word build of the paper (runs after citeproc).
--  * numbers sections (I., A.), figures (Fig. 1.) and tables (Table I.) the way the PDF does and rewrites every \ref to match
--  * turns \pending{...} and \todo{...} (marked by prepare.py as links to PENDING and TODO) into spans of the character styles Pending and Todo,
--    which build_docx.py then highlights red and yellow
--  * puts the [VERIFY] note of every bibliography entry into a Word comment on that reference
local notes = dofile(os.getenv("VERIFY_NOTES"))

local function roman(n)
  local vals = { { 10, "X" }, { 9, "IX" }, { 5, "V" }, { 4, "IV" }, { 1, "I" } }
  local out = ""
  for _, p in ipairs(vals) do
    while n >= p[1] do out = out .. p[2]; n = n - p[1] end
  end
  return out
end

local function letter(n) return string.char(64 + n) end

local labels = {}

local function prefix_caption(caption, text)
  local first = caption.long[1]
  if first and (first.t == "Plain" or first.t == "Para") then
    table.insert(first.content, 1, pandoc.Space())
    table.insert(first.content, 1, pandoc.Strong({ pandoc.Str(text) }))
  else
    table.insert(caption.long, 1, pandoc.Para({ pandoc.Strong({ pandoc.Str(text) }) }))
  end
end

function Pandoc(doc)
  local sec, sub, fig, tab = 0, 0, 0, 0
  -- pass 1: numbering and caption prefixes
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and not b.classes:includes("unnumbered") then
      if b.level == 1 then
        sec = sec + 1
        sub = 0
        labels[b.identifier] = roman(sec)
        table.insert(b.content, 1, pandoc.Space())
        table.insert(b.content, 1, pandoc.Str(roman(sec) .. "."))
      elseif b.level == 2 then
        sub = sub + 1
        labels[b.identifier] = roman(sec) .. "-" .. letter(sub)
        table.insert(b.content, 1, pandoc.Space())
        table.insert(b.content, 1, pandoc.Str(letter(sub) .. "."))
      end
    elseif b.t == "Figure" then
      fig = fig + 1
      labels[b.identifier] = tostring(fig)
      prefix_caption(b.caption, "Fig. " .. fig .. ".")
    elseif b.t == "Table" then
      tab = tab + 1
      labels[b.identifier] = roman(tab)
      prefix_caption(b.caption, "Table " .. roman(tab) .. ".")
    end
  end
  -- pass 2: references, pending and todo markers
  doc = doc:walk({
    Link = function(l)
      if l.target == "PENDING" then
        return pandoc.Span(l.content, pandoc.Attr("", {}, { { "custom-style", "Pending" } }))
      elseif l.target == "TODO" then
        return pandoc.Span(l.content, pandoc.Attr("", {}, { { "custom-style", "Todo" } }))
      end
      local id = l.target:match("^#(.+)$")
      if id and labels[id] then
        return pandoc.Str(labels[id])
      end
    end,
  })
  -- pass 3: VERIFY comments on the references
  local n = 0
  doc = doc:walk({
    Div = function(d)
      local key = d.identifier:match("^ref%-(.+)$")
      if key and notes[key] and d.content[1] and d.content[1].content then
        n = n + 1
        local para = d.content[1]
        local text = "[VERIFY] Check title, authors, venue, year and pages against the publisher page. " .. notes[key]
        local start = pandoc.Span({ pandoc.Str(text) }, pandoc.Attr("", { "comment-start" }, { { "id", tostring(n) }, { "author", "Claude" }, { "date", "2026-11-02T12:00:00Z" } }))
        local stop = pandoc.Span({}, pandoc.Attr("", { "comment-end" }, { { "id", tostring(n) } }))
        table.insert(para.content, 1, start)
        table.insert(para.content, stop)
        return d
      end
    end,
  })
  return doc
end
