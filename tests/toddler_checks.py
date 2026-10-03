"""Toddler-proofing: ghost taps, mashing, stay-in-lines help, and tracing rewards."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app_target import APP_URL
from playwright.sync_api import sync_playwright
URL=APP_URL
with sync_playwright() as p:
    browser=p.chromium.launch()
    for w,h in [(1024,768),(390,844)]:
        page=browser.new_page(viewport={'width':w,'height':h},has_touch=True)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
        page.evaluate('soundOn=false')
        # The tap that opens the picker must not close it or pick a page.
        page.locator('#btnPaper').tap();page.wait_for_timeout(250)
        assert page.locator('#paperSheet').is_visible(),w
        # An eager second tap right away lands on a tile but is ignored.
        page.locator('[data-paper="fish"]').tap()
        assert page.locator('#paperSheet').is_visible() and page.evaluate('paperId')=='butterfly',w
        # Tapping beside the cards never closes the picker.
        page.touchscreen.tap(3,h/2);page.wait_for_timeout(650)
        assert page.locator('#paperSheet').is_visible(),w
        page.locator('[data-paper="fish"]').tap();before=page.evaluate('artRevision')
        # The same finger tapping again does not scribble on the new page.
        page.touchscreen.tap(w/2,h/2)
        assert page.evaluate('artRevision')==before,w
        assert page.locator('#paperSheet').is_hidden() and page.evaluate('paperId')=='fish',w
        # Mashing Next picture advances once.
        page.wait_for_timeout(650)
        box=page.locator('#btnNext').bounding_box()
        for _ in range(3):page.touchscreen.tap(box['x']+box['width']/2,box['y']+box['height']/2);page.wait_for_timeout(150)
        assert page.evaluate('paperId')=='cat',(w,page.evaluate('paperId'))
        assert not errors,errors
        page.close()

    page=browser.new_page(viewport={'width':1280,'height':900})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate("soundOn=false;localStorage.removeItem('artstudio-settings');settings.stars=0;settings.helper=true")
    def world(u,v):
        return page.evaluate('([u,v])=>{const s=Math.min(designWidth,designHeight)*.82;return [vw/2+(u-50)*s/100,vh/2+(v-50)*s/100]}',[u,v])
    def screen(x,y):
        r=page.locator('#hit').bounding_box();scale,left,top=page.evaluate('[viewScale,viewLeft,viewTop]')
        return r['x']+left+x*scale,r['y']+top+y*scale
    def alpha(x,y):return page.evaluate('([x,y])=>actx.getImageData(Math.floor(x*dpr),Math.floor(y*dpr),1,1).data[3]',[x,y])
    def scribble(start,end):
        page.mouse.move(*screen(*start));page.mouse.down();page.mouse.move(*screen(*end),steps=30);page.mouse.up()
    # A stroke that starts inside a butterfly wing stays inside that wing.
    page.evaluate("setTool('marker');setColor('#1e88e5')");page.wait_for_timeout(400)
    inside,outside=world(31,27),world(25,6)
    scribble(inside,outside)
    assert alpha(*inside)>0 and alpha(*outside)==0,(alpha(*inside),alpha(*outside))
    # The live preview obeys the same edge while the finger is still down.
    page.mouse.move(*screen(*inside));page.mouse.down();page.mouse.move(*screen(*outside),steps=20);page.wait_for_timeout(50)
    assert page.evaluate('([x,y])=>lctx.getImageData(Math.floor(x*dpr),Math.floor(y*dpr),1,1).data[3]',outside)==0
    page.mouse.up()
    # Strokes that start on the open background, or with the helper off, draw freely.
    page.evaluate('settings.helper=false')
    scribble(inside,outside);assert alpha(*outside)>0
    page.evaluate('settings.helper=true;freshPage()')
    scribble(world(4,50),world(40,38));assert alpha(*world(40,38))>0
    # Following a tracing line earns a star; scribbling elsewhere does not.
    page.evaluate("choosePaper({dataset:{paper:'trace-shapes'}});setTool('crayon')");page.wait_for_timeout(300)
    import math
    page.mouse.move(*screen(*world(5,5)));page.mouse.down()
    for i in range(0,40):page.mouse.move(*screen(*world(5+i*2,5)))
    page.mouse.up()
    assert page.evaluate('settings.stars')==0
    ring=[world(27+17*math.cos(a/40*math.tau),29+17*math.sin(a/40*math.tau)) for a in range(41)]
    page.mouse.move(*screen(*ring[0]));page.mouse.down()
    for pt in ring[1:]:page.mouse.move(*screen(*pt),steps=3)
    page.mouse.up()
    assert page.evaluate('settings.stars')==1
    assert page.locator('#stars').is_visible() and page.locator('#starCount').inner_text()=='1'
    assert not errors,errors
    browser.close()
    print('PASS: opening taps settle, beside-card taps ignored, no post-pick scribbles, mashing advances once, strokes stay in shapes, tracing earns stars')
