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
        for selector in ['#actions button:visible','#rail button:not([hidden])','#bottom button','#side button:visible']:
            for box in page.locator(selector).evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})'):
                assert box['w']>=(48 if selector=='#bottom button' and ((w<560 and h<700) or h<500) else 56) and box['h']>=(48 if selector=='#bottom button' and ((w<560 and h<700) or h<500) else 56),(w,h,selector,box)
                assert box['x']>=0 and box['y']>=0 and box['x']+box['w']<=w and box['y']+box['h']<=h,(w,h,selector,box)
        assert page.locator('#rail .tool:visible').count()==12
        panels=[page.locator(sel).bounding_box() for sel in (['#rail','#ui > #side','#bottom','#actions'] if page.locator('#ui > #side').count() else ['#rail','#bottom','#actions'])]
        for i,a in enumerate(panels):
            for b in panels[i+1:]:
                assert a['x']+a['width']<=b['x'] or b['x']+b['width']<=a['x'] or a['y']+a['height']<=b['y'] or b['y']+b['height']<=a['y'],(w,h,a,b)
        assert page.locator('.sw:visible').count()==14
        assert page.locator('#moreColors').count()==0
        assert page.evaluate('''()=>{const b=drawingBounds(),size=Math.min(designWidth,designHeight)*.82*viewScale;const cx=viewLeft+vw*viewScale/2,cy=viewTop+vh*viewScale/2;return cx-size/2>=b.x && cx+size/2<=b.x+b.width && cy-size/2>=b.y && cy+size/2<=b.y+b.height;}''')
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
    # A slight miss in the palette padding still picks the nearest color.
    box=page.locator('[data-color="#e53935"]').bounding_box()
    page.touchscreen.tap(box['x']-5,box['y']+20)
    assert page.evaluate('color')=='#e53935' and page.evaluate('colorPicks')==3
    page.locator('[data-tool="crayon"]').tap()
    previous=page.evaluate('paperId')
    page.locator('#btnNext').tap()
    assert page.evaluate('paperId')!=previous and page.evaluate('tool')=='crayon'
    page.locator('#btnUndo').tap()
    assert page.evaluate('paperId')==previous
    print('PASS: large touch targets, six viewport layouts, all 12 tools visible, non-overlapping panels, single touch activation, near misses, undoable picture changes')
    browser.close()
