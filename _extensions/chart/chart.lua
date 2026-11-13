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
    local height = pandoc.utils.stringify(kwargs["height"] or "")
    if height == "" then height = (c.kind == "map") and "820" or "640" end
    return pandoc.RawBlock("html", string.format(
      '<figure class="ibn-chart"><iframe src="/charts/%s.html" data-chart="%s" title="%s" ' ..
      'width="100%%" height="%s" style="border:0" loading="lazy"></iframe></figure>',
      esc(id), esc(id), esc(c.title), esc(height)))
  end
}
