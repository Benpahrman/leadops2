with open('agents/templates/portal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all ${...} patterns
idx = 0
while True:
    idx = content.find('${', idx)
    if idx == -1:
        break
    end = content.find('}', idx)
    if end == -1:
        break
    print(repr(content[idx:end+1]))
    idx = end + 1