"""Touch target, pen slip, and duplicate click regression checks."""
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(has_touch=True)
    page.goto((Path(__file__).resolve().parents[1]/'write_v5.html').as_uri())
    page.click('#setupDone')
    for w,h in [(1366,768),(1024,768),(768,1024),(390,844),(320,568),(844,390)]:
        page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(300)
        for selector in ['#actions button','#rail button:not([hidden])','#bottom button','#side button']:
            for box in page.locator(selector).evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})'):
                assert box['w']>=56 and box['h']>=56,(w,h,selector,box)
                assert box['x']>=0 and box['y']>=0 and box['x']+box['w']<=w and box['y']+box['h']<=h,(w,h,selector,box)
        if w>=1024:
            assert page.locator('.sw').count()==14
        page.screenshot(path=f'/tmp/art-{w}-{h}.png')
    page.set_viewport_size({'width':1366,'height':768});page.wait_for_timeout(300)
    # A real touch changes color exactly once, even though the palette rebuilds.
    page.evaluate('()=>{window.colorPicks=0;const original=setColor;setColor=c=>{colorPicks++;original(c)}}')
    page.locator('[data-color="#1e88e5"]').tap()
    assert page.evaluate('color')=='#1e88e5'
    assert page.evaluate('colorPicks')==1
    # A captured pen tap may land near an edge and lift just outside the tile.
    page.evaluate('''()=>{const b=document.querySelector('[data-color="#fdd835"]');const r=b.getBoundingClientRect();
      b.setPointerCapture=()=>{};
      b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:12,pointerType:'pen',clientX:r.right-2,clientY:r.top+20}));
      b.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:12,pointerType:'pen',clientX:r.right+12,clientY:r.top+20}));}''')
    assert page.evaluate('color')=='#fdd835'
    assert page.evaluate('colorPicks')==2
    print('PASS: 56px minimum targets, six viewport layouts, all desktop colors, single touch activation, forgiving pen tap')
    browser.close()
