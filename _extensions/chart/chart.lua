-- {{< chart <id> >}} shows charts/<id>.html in a frame that sizes itself to
-- the chart. The title and default height come from charts/index.json.
-- A chart that hasn't been built yet shows a placeholder, so the site still builds.

local index = nil

local function load_index()
  if index then return index end
  index = {}
  local dir = quarto.project.directory or "."
  local f = io.open(dir .. "/charts/index.json", "r")
  if f then
    local ok, charts = pcall(quarto.json.decode, f:read("a"))
    f:close()
    if ok and charts then
      for _, c in ipairs(charts) do index[c.id] = c end
    end
  end
  return index
end

local function esc(s)
  return (tostring(s):gsub("&", "&amp;"):gsub('"', "&quot;"):gsub("<", "&lt;"))
end


-- Read a YAML file whose top level is a mapping, by handing it to pandoc as
-- a document's metadata block.
local function read_yaml(name)
  local dir = quarto.project.directory or "."
  local f = io.open(dir .. "/" .. name, "r")
  if not f then return nil end
  local text = f:read("a")
  f:close()
  return pandoc.read("---\n" .. text .. "\n---\n", "markdown").meta
end

local function str(v)
  if v == nil then return "" end
  return pandoc.utils.stringify(v)
end

-- Blocks from a metadata value, keeping links and emphasis.
local function blocks(v)
  if v == nil then return {} end
  if pandoc.utils.type(v) == "Blocks" then return v end
  return { pandoc.Para(v) }
end

local function long_date(iso)
  local y, m, d = iso:match("(%d+)-(%d+)-(%d+)")
  if not y then return iso end
  local months = {"January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"}
  return tonumber(d) .. " " .. months[tonumber(m)] .. " " .. y
end

local function frame(c, height)
  if height == nil or height == "" then height = (c.kind == "map") and "820" or "640" end
  return string.format(
    '<figure class="ibn-chart"><iframe src="/charts/%s.html" data-chart="%s" title="%s" ' ..
    'width="100%%" height="%s" style="border:0" loading="lazy"></iframe></figure>',
    esc(c.id), esc(c.id), esc(c.title), esc(height))
end
return {
  ["chart"] = function(args, kwargs)
    local id = pandoc.utils.stringify(args[1])
    if not quarto.doc.is_format("html") then
      return pandoc.Para({pandoc.Link("Chart: " .. id, "/charts/" .. id .. ".html")})
    end
    local c = load_index()[id]
    if not c then
      quarto.log.warning("chart " .. id .. " is not in charts/index.json yet")
      return pandoc.RawBlock("html",
        '<div class="ibn-chart-missing">Chart <code>' .. esc(id) .. '</code> is on the way.</div>')
    end
    return pandoc.RawBlock("html", frame(c, pandoc.utils.stringify(kwargs["height"] or "")))
  end,

  -- {{< key-facts population-total population-change >}} lists the key fact of
  -- each chart named, in that order, each linked to its chart. The facts are
  -- worked out from the data when the charts are built, so they stay current.
  -- {{< key-facts population >}} lists every chart in a topic.
  ["key-facts"] = function(args)
    local idx = load_index()
    local wanted = {}
    for _, a in ipairs(args) do
      local name = pandoc.utils.stringify(a)
      if idx[name] then
        table.insert(wanted, idx[name])
      else
        local dir = quarto.project.directory or "."
        local f = io.open(dir .. "/charts/index.json", "r")
        if f then
          local ok, charts = pcall(quarto.json.decode, f:read("a"))
          f:close()
          for _, c in ipairs(ok and charts or {}) do
            if c.topic == name and c.listed ~= false then table.insert(wanted, c) end
          end
        end
      end
    end
    local items = {}
    for _, c in ipairs(wanted) do
      if c.key_fact and c.key_fact ~= "" then
        table.insert(items, string.format('<li>%s <a href="%s" class="key-fact-link">%s</a></li>',
          esc(c.key_fact), esc(c.page), "See the chart"))
      end
    end
    if #items == 0 then return pandoc.Null() end
    return pandoc.RawBlock("html", '<section class="key-facts" aria-labelledby="key-facts-h">' ..
      '<h2 id="key-facts-h" class="key-facts-label">Key facts</h2><ul>' ..
      table.concat(items) .. '</ul></section>')
  end,

  -- {{< chart-of-the-week >}} shows the newest entry in chart-of-the-week.yml,
  -- {{< chart-of-the-week all >}} lists every entry, newest first.
  ["chart-of-the-week"] = function(args)
    local meta = read_yaml("chart-of-the-week.yml")
    if not meta or not meta.weeks then return pandoc.Null() end
    local weeks = {}
    for _, w in ipairs(meta.weeks) do table.insert(weeks, w) end
    table.sort(weeks, function(a, b) return str(a.date) > str(b.date) end)
    local all = args[1] and pandoc.utils.stringify(args[1]) == "all"
    local out = {}
    local idx = load_index()
    for i, w in ipairs(weeks) do
      local c = idx[str(w.chart)]
      if c then
        if all then
          table.insert(out, pandoc.Header(2, pandoc.Link(c.title, c.page), pandoc.Attr("week-" .. str(w.date))))
          table.insert(out, pandoc.Para({pandoc.Emph(long_date(str(w.date)))}))
          for _, b in ipairs(blocks(w.note)) do table.insert(out, b) end
        else
          table.insert(out, pandoc.Para({pandoc.Span(long_date(str(w.date)), pandoc.Attr("", {"cotw-date"}))}))
          for _, b in ipairs(blocks(w.note)) do table.insert(out, b) end
          table.insert(out, pandoc.RawBlock("html", frame(c)))
          break
        end
      else
        quarto.log.warning("chart of the week " .. str(w.chart) .. " is not in charts/index.json")
      end
    end
    return out
  end,

  -- {{< irish population >}} shows a topic's Irish title and summary from
  -- irish.yml, once that file is marked approved.
  ["irish"] = function(args)
    local meta = read_yaml("irish.yml")
    if not meta or not meta.approved or not meta.topics then return pandoc.Null() end
    local t = meta.topics[pandoc.utils.stringify(args[1])]
    if not t then return pandoc.Null() end
    return pandoc.Div({
      pandoc.Para({pandoc.Strong(str(t.title))}),
      pandoc.Para(t.summary or {}),
    }, pandoc.Attr("", {"irish"}, {lang = "ga"}))
  end,
}
