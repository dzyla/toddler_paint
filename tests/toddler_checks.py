"""Toddler-proofing: instant taps, harmless mashing, stay-in-lines help, and tracing rewards."""
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
        # The picker opens on the tap that presses New page.
        page.locator('#btnPaper').tap();page.wait_for_timeout(150)
        assert page.locator('#paperSheet').is_visible(),w
        # An eager second tap on a card is honoured at once: no dead half-second.
        page.locator('[data-paper="fish"]').tap();page.wait_for_timeout(150)
        assert page.locator('#paperSheet').is_hidden() and page.evaluate('paperId')=='fish',w
        # Tapping beside the cards never closes the picker.
        page.locator('#btnPaper').tap();page.wait_for_timeout(150)
        page.touchscreen.tap(3,h/2);page.wait_for_timeout(150)
        assert page.locator('#paperSheet').is_visible(),w
        page.locator('[data-paper="cat"]').tap();before=page.evaluate('artRevision')
        # The finger that just chose a page does not scribble on it.
        page.wait_for_timeout(160)
        assert page.evaluate('artRevision')==before,w
        assert page.locator('#paperSheet').is_hidden() and page.evaluate('paperId')=='cat',w
        # Three taps on Next picture advance three times: silence is what frustrates him.
        # Next picture sits on the right edge, which phones keep in the grown-up
        # menu, because there the gallery covers picture-changing.
        if not page.evaluate('phoneLayout()'):
            page.wait_for_timeout(200)
            box=page.locator('#btnNext').bounding_box()
            for _ in range(3):
                page.touchscreen.tap(box['x']+box['width']/2,box['y']+box['height']/2);page.wait_for_timeout(150)
            assert page.evaluate('paperId')=='rocket',(w,page.evaluate('paperId'))
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

    # --- Task 2: the tap engine answers every tap ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')

    # No cooldown attributes survive.
    assert page.evaluate("document.querySelectorAll('[data-cooldown]').length")==0

    # Ten rapid taps on a tool all register, none suppressed.
    page.evaluate("()=>{window.toolCalls=0;const o=setTool;setTool=k=>{toolCalls++;o(k)}}")
    box=page.locator('[data-tool="pencil"]').bounding_box()
    cx,cy=box['x']+box['width']/2,box['y']+box['height']/2
    for _ in range(10):
        page.touchscreen.tap(cx,cy);page.wait_for_timeout(30)
    assert page.evaluate('toolCalls')==10,page.evaluate('toolCalls')
    assert page.evaluate('tool')=='pencil'

    # One gesture fires one action: pointerdown activation must not double-fire
    # alongside the browser's native click.
    page.evaluate("()=>{window.toolCalls=0}")
    page.locator('[data-tool="marker"]').tap();page.wait_for_timeout(150)
    assert page.evaluate('toolCalls')==1,page.evaluate('toolCalls')
    page.evaluate("()=>{window.toolCalls=0}")
    page.locator('[data-tool="crayon"]').click();page.wait_for_timeout(150)
    assert page.evaluate('toolCalls')==1,page.evaluate('toolCalls')

    # Two fingers landing on two controls at once: both register, neither
    # button stays stuck in .press.
    page.evaluate("()=>{window.toolCalls=0}")
    page.evaluate("""()=>{
      const a=document.querySelector('[data-tool="pencil"]'),b=document.querySelector('[data-tool="spray"]');
      const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();
      const send=(el,r,id,type)=>el.dispatchEvent(new PointerEvent(type,
        {bubbles:true,pointerId:id,pointerType:'touch',clientX:r.left+r.width/2,clientY:r.top+r.height/2}));
      a.setPointerCapture=()=>{};b.setPointerCapture=()=>{};
      send(a,ra,21,'pointerdown');send(b,rb,22,'pointerdown');
      send(a,ra,21,'pointerup');send(b,rb,22,'pointerup');
    }""")
    page.wait_for_timeout(300)
    assert page.evaluate('toolCalls')==2,page.evaluate('toolCalls')
    assert page.evaluate("document.querySelectorAll('.press').length")==0

    # A tap equidistant between two adjacent action tiles selects neither.
    gap=page.evaluate("""()=>{
      const p=document.getElementById('btnPaper'),n=document.getElementById('btnNew');
      const a=p.getBoundingClientRect(),b=n.getBoundingClientRect();
      return [(a.right+b.left)/2,(a.top+a.bottom)/2];
    }""")
    assert page.evaluate('([x,y])=>resolveTapTarget(document.getElementById("actions"),x,y)===null',gap)

    # An unambiguous near miss still snaps to the nearest tile.
    near=page.evaluate("""()=>{const p=document.getElementById('btnPaper');
      const r=p.getBoundingClientRect();return [r.left-12,(r.top+r.bottom)/2];}""")
    assert page.evaluate('([x,y])=>resolveTapTarget(document.getElementById("actions"),x,y)?.id==="btnPaper"',near)
    assert not errors,errors

    # --- Task 3: a resting finger must not kill the interface ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    page.evaluate("choosePaper({dataset:{paper:'white'}});setTool('crayon')")
    page.wait_for_timeout(250)

    hit=page.locator('#hit').bounding_box()
    hx,hy=hit['x']+hit['width']/2,hit['y']+hit['height']/2
    def finger(type_,pid,x,y):
        page.evaluate("""([type,pid,x,y])=>{
          const h=document.getElementById('hit');
          h.setPointerCapture=()=>{};
          h.dispatchEvent(new PointerEvent(type,{bubbles:true,pointerId:pid,pointerType:'touch',
            isPrimary:true,clientX:x,clientY:y,pressure:.5}));
        }""",[type_,pid,x,y])

    # A finger parked on the paper: the tool still changes.
    finger('pointerdown',31,hx,hy)
    page.wait_for_timeout(500)
    assert page.evaluate('activeId')==31,page.evaluate('activeId')
    assert page.evaluate('drawingNow()')==False
    page.locator('[data-tool="pencil"]').tap();page.wait_for_timeout(150)
    assert page.evaluate('tool')=='pencil',page.evaluate('tool')
    finger('pointerup',31,hx,hy)

    # A stroke that is actively moving still blocks a tool change.
    finger('pointerdown',32,hx,hy)
    for i in range(6):
        finger('pointermove',32,hx+i*9,hy+i*7);page.wait_for_timeout(16)
    assert page.evaluate('drawingNow()')==True
    page.locator('[data-tool="marker"]').tap();page.wait_for_timeout(60)
    assert page.evaluate('tool')=='pencil',page.evaluate('tool')
    finger('pointerup',32,hx+60,hy+50)
    page.wait_for_timeout(100)

    # A lost pointerup must not lock the paper forever.
    finger('pointerdown',33,hx,hy)
    page.wait_for_timeout(150)
    page.evaluate('()=>{stroke.lastMoveAt=performance.now()-9999}')
    assert page.evaluate('strokeIdleFor()')>2500
    before=page.evaluate('artRevision')
    finger('pointerdown',34,hx+40,hy+40)
    page.wait_for_timeout(100)
    assert page.evaluate('activeId')==34,page.evaluate('activeId')
    assert page.evaluate('artRevision')>before,(page.evaluate('artRevision'),before)
    finger('pointerup',34,hx+40,hy+40)
    assert not errors,errors

    # --- Task 4: mashing must cost him nothing ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    page.evaluate("choosePaper({dataset:{paper:'white'}});setTool('crayon')")
    page.wait_for_timeout(250)
    page.evaluate('history_.reset()')

    assert page.evaluate('artIsEmpty()')==True

    # artIsEmpty runs on the Clean path he is expected to mash, so it must be
    # cheap on the largest canvas, not merely under a frame: the old full
    # getImageData allocated ~20MB per tap.
    cost=max(page.evaluate('()=>{const t=performance.now();artIsEmpty();return performance.now()-t}')
             for _ in range(5))
    assert cost<3,cost
    # Cheap must not mean blind: a single short stroke still counts as ink.
    hitb=page.locator('#hit').bounding_box()
    page.mouse.move(hitb['x']+hitb['width']*.5,hitb['y']+hitb['height']*.5)
    page.mouse.down();page.mouse.move(hitb['x']+hitb['width']*.5+14,hitb['y']+hitb['height']*.5+10)
    page.mouse.up();page.wait_for_timeout(250)
    assert page.evaluate('artIsEmpty()')==False
    page.evaluate('freshPage()');page.wait_for_timeout(200)
    assert page.evaluate('artIsEmpty()')==True

    # Draw something, then mash Clean ten times.
    hit=page.locator('#hit').bounding_box()
    page.mouse.move(hit['x']+hit['width']*.4,hit['y']+hit['height']*.4)
    page.mouse.down()
    for i in range(10):page.mouse.move(hit['x']+hit['width']*.4+i*12,hit['y']+hit['height']*.4+i*9)
    page.mouse.up();page.wait_for_timeout(250)
    assert page.evaluate('artIsEmpty()')==False
    depth=page.evaluate('()=>undoDepth()')

    box=page.locator('#btnNew').bounding_box()
    cx,cy=box['x']+box['width']/2,box['y']+box['height']/2
    # Count pushes rather than compare undo depth: history_.trim() caps depth by
    # total snapshot bytes, and one snapshot of a full-size canvas is already
    # ~20MB, so depth saturates at 2 regardless of how many entries were made.
    page.evaluate("()=>{window.pushes=0;const o=history_.push;history_.push=()=>{pushes++;o.call(history_)}}")
    for _ in range(10):
        page.touchscreen.tap(cx,cy);page.wait_for_timeout(60)
    assert page.evaluate('artIsEmpty()')==True
    # Exactly one history entry for ten taps: the nine no-ops are free.
    assert page.evaluate('pushes')==1,page.evaluate('pushes')
    # And one Undo brings his drawing back.
    page.locator('#btnUndo').tap();page.wait_for_timeout(350)
    assert page.evaluate('artIsEmpty()')==False

    # Re-choosing the page already open just closes the gallery.
    page.locator('#btnPaper').tap();page.wait_for_timeout(200)
    page.locator('[data-category="plain"]').tap();page.wait_for_timeout(200)
    depth=page.evaluate('()=>undoDepth()')
    revision=page.evaluate('artRevision')
    page.locator('[data-paper="white"]').tap();page.wait_for_timeout(200)
    assert page.locator('#paperSheet').is_hidden()
    assert page.evaluate('()=>undoDepth()')==depth,(page.evaluate('()=>undoDepth()'),depth)
    assert page.evaluate('artRevision')==revision
    assert not errors,errors

    # --- Task 5: New page is an on/off toggle ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')

    paper=page.locator('#btnPaper')
    paper.tap();page.wait_for_timeout(200)
    assert page.locator('#paperSheet').is_visible()
    # The button he pressed stays visible and reachable above the gallery.
    assert paper.is_visible()
    assert page.evaluate("""()=>{const b=document.getElementById('btnPaper');
      const r=b.getBoundingClientRect();
      const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
      return hit===b || b.contains(hit);}""")
    assert paper.get_attribute('aria-expanded')=='true'
    # Second tap closes it.
    paper.tap();page.wait_for_timeout(200)
    assert page.locator('#paperSheet').is_hidden()
    assert paper.get_attribute('aria-expanded')=='false'
    # Third tap reopens immediately: no cooldown.
    paper.tap();page.wait_for_timeout(200)
    assert page.locator('#paperSheet').is_visible()
    # The toggle reads the DOM, so closing by Back keeps it in step.
    page.locator('#paperFoot .closeSheet').tap();page.wait_for_timeout(200)
    assert page.locator('#paperSheet').is_hidden()
    assert paper.get_attribute('aria-expanded')=='false'
    paper.tap();page.wait_for_timeout(200)
    assert page.locator('#paperSheet').is_visible()
    page.locator('#paperFoot .closeSheet').tap();page.wait_for_timeout(200)
    assert page.locator('#paperSheet').is_hidden()

    # Choosing a page must size the paper against the real top bar. While the
    # gallery is open the cluster is parented to the body, so measuring then
    # would report a short top row and make the page too tall.
    page.locator('#btnPaper').tap();page.wait_for_timeout(200)
    page.locator('[data-paper="dog"]').tap();page.wait_for_timeout(400)
    via_gallery=page.evaluate('designHeight')
    page.evaluate("choosePaper({dataset:{paper:'fish'}})");page.wait_for_timeout(400)
    direct=page.evaluate('designHeight')
    assert abs(via_gallery-direct)<=1,(via_gallery,direct)
    assert not errors,errors

    # --- Task 6: six bold cards he can actually tell apart ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    for vw_,vh_ in [(1366,768),(1024,768),(768,1024),(390,844),(320,568),
                    (375,667),(600,960),(844,390),(667,375),(568,320)]:
        page.set_viewport_size({'width':vw_,'height':vh_});page.wait_for_timeout(300)
        size=page.evaluate('paperGridSize()')
        # Six is the ceiling, not a quota. On a cramped screen the rows drop so
        # each card stays big enough to recognise; squeezing six in made the
        # previews 40px tall, which defeats the point of the picker.
        cells=size['cols']*size['rows']
        assert 2<=cells<=6,(vw_,vh_,size)
        assert size['cols']==(2 if (vh_>vw_ and page.evaluate('phoneLayout()')) else 3),(vw_,vh_,size)
        if (vw_,vh_) in [(1366,768),(1024,768),(768,1024),(390,844),(600,960)]:
            assert cells==6,(vw_,vh_,size)
        page.locator('#btnPaper').tap();page.wait_for_timeout(250)
        cards=page.locator('#pictureGrid .b:visible').count()
        assert 0<cards<=6,(vw_,vh_,cards)
        # No scrolling anywhere in the picker.
        assert page.evaluate("()=>{const c=document.getElementById('paperCard');"
                             "return c.scrollHeight<=c.clientHeight+1 && c.scrollWidth<=c.clientWidth+1}"),(vw_,vh_)
        # Previews are drawn boldly enough to read at arm's length.
        assert page.evaluate("()=>PREVIEW_LINE>=2.5")
        page.locator('#btnPaper').tap();page.wait_for_timeout(200)
    page.set_viewport_size({'width':1024,'height':768});page.wait_for_timeout(300)

    # Four tabs: Words needs typing, so it lives with the grown-ups now.
    page.locator('#btnPaper').tap();page.wait_for_timeout(250)
    assert page.locator('#paperTabs button').count()==4
    assert page.locator('#paperTabs [data-category="words"]').count()==0

    # The gallery always opens on the first page, so the cards he knows are in
    # the same places every time. With six per page, a remembered page number
    # would hide the Surprise card and the familiar first pictures.
    page.locator('#paperNext').tap();page.wait_for_timeout(200)
    assert page.evaluate('paperPage')==1
    page.locator('#btnPaper').tap();page.wait_for_timeout(200)
    page.locator('#btnPaper').tap();page.wait_for_timeout(250)
    assert page.evaluate('paperPage')==0,page.evaluate('paperPage')
    assert page.locator('#surprise').count()==1
    page.locator('#btnPaper').tap();page.wait_for_timeout(200)
    assert not errors,errors

    # --- Task 7: three tiles he can tell apart and cannot confuse ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    for vw_,vh_ in [(1366,768),(1024,768),(768,1024),(390,844),(320,568),
                    (375,667),(600,960),(844,390),(667,375),(568,320)]:
        page.set_viewport_size({'width':vw_,'height':vh_});page.wait_for_timeout(300)
        phone=page.evaluate('phoneLayout()')
        ids=page.evaluate("()=>[...document.querySelectorAll('#actions button')]"
                          ".filter(b=>b.offsetParent).map(b=>b.id)")
        assert ids==['btnUndo','btnPaper','btnNew'],(vw_,vh_,ids)
        floor=page.evaluate('clusterMinSize()')
        assert floor==(64 if phone else 96),(vw_,vh_,floor,phone)
        for id_ in ids:
            box=page.locator('#'+id_).bounding_box()
            assert box['width']>=floor-.5 and box['height']>=floor-.5,(vw_,vh_,id_,box,floor)
        # A slip off New page must not be able to reach Clean.
        gap=page.evaluate("""()=>{const p=document.getElementById('btnPaper').getBoundingClientRect();
          const n=document.getElementById('btnNew').getBoundingClientRect();return n.left-p.right;}""")
        assert gap>=15.5,(vw_,vh_,gap)
        # Three channels of difference: colour, shape, icon size.
        shapes=page.evaluate("()=>['btnUndo','btnPaper','btnNew'].map(i=>{"
                             "const s=getComputedStyle(document.getElementById(i));"
                             "return s.borderRadius+'|'+s.backgroundColor})")
        assert len(set(shapes))==3,(vw_,vh_,shapes)
        # Larger controls must not starve the paper. Half the viewport is the
        # hard rule on phones. Tablet portrait at 768x1024 sat at .492 before any
        # of this work, because the tool rail and the palette each wrap to two
        # rows at that width; it is pinned here so it cannot slide further.
        ratio=page.evaluate('drawingBounds().height/viewH()')
        assert ratio>=(.5 if phone else .46),(vw_,vh_,ratio,phone)
        # Right edge: Next picture plus three sizes, no mirror.
        if not phone:
            side=page.evaluate("()=>[...document.querySelectorAll('#side button')]"
                               ".filter(b=>b.offsetParent).map(b=>b.id||b.dataset.size)")
            assert side==['btnNext','small','medium','large'],(vw_,vh_,side)
    page.set_viewport_size({'width':1024,'height':768});page.wait_for_timeout(300)
    assert page.evaluate("!!document.getElementById('btnRedo')")==False
    assert page.evaluate("!!document.getElementById('btnMirror')")==False
    assert not errors,errors

    # --- Task 8: a tap that changes nothing still answers ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    page.evaluate("()=>{window.chimes=[];const o=chime;window.chime=(f,ty,v,l)=>{chimes.push([f,v===undefined?.07:v]);o(f,ty,v,l)}}")

    # Re-tapping the tool already chosen: press animation and a softer chime.
    page.evaluate("setTool('crayon')")
    page.evaluate('()=>{chimes.length=0}')
    page.locator('[data-tool="crayon"]').tap();page.wait_for_timeout(250)
    assert page.evaluate('chimes.length')>=1,page.evaluate('chimes')
    quiet=page.evaluate('chimes[chimes.length-1][1]')

    page.evaluate('()=>{chimes.length=0}')
    page.locator('[data-tool="pencil"]').tap();page.wait_for_timeout(250)
    loud=page.evaluate('chimes[chimes.length-1][1]')
    assert quiet<loud,(quiet,loud)

    # Re-tapping the colour already chosen is answered the same way.
    page.evaluate("()=>{const sw=document.querySelector('.sw.on');window.currentColor=sw&&sw.dataset.color}")
    current=page.evaluate('currentColor')
    page.evaluate('()=>{chimes.length=0}')
    page.locator(f'[data-color="{current}"]').tap();page.wait_for_timeout(250)
    quiet_c=page.evaluate('chimes[chimes.length-1][1]')
    page.evaluate('()=>{chimes.length=0}')
    other='#1e88e5' if current!='#1e88e5' else '#e53935'
    page.locator(f'[data-color="{other}"]').tap();page.wait_for_timeout(250)
    loud_c=page.evaluate('chimes[chimes.length-1][1]')
    assert quiet_c<loud_c,(quiet_c,loud_c)

    # Every engine-owned tap flashes .press, changed or not.
    flashed=page.evaluate("""()=>new Promise(resolve=>{
      const b=document.querySelector('[data-tool="pencil"]');
      let seen=false;
      const mo=new MutationObserver(()=>{if(b.classList.contains('press'))seen=true});
      mo.observe(b,{attributes:true,attributeFilter:['class']});
      const r=b.getBoundingClientRect();
      b.setPointerCapture=()=>{};
      b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:41,pointerType:'touch',
        clientX:r.left+r.width/2,clientY:r.top+r.height/2}));
      setTimeout(()=>{mo.disconnect();resolve(seen)},100);
    })""")
    assert flashed==True
    assert not errors,errors

    # --- Review fix 1: cards must stay big enough to see on short screens ---
    # Counting cards and checking PREVIEW_LINE proves nothing the child's eye
    # can see: the backing canvas is scaled down to fit the cell, so a squeezed
    # cell renders a 2.6px line at a fraction of a pixel. Measure the rendered
    # box instead, on the layouts that squeeze hardest.
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    for vw_,vh_ in [(568,320),(640,360),(812,375),(360,640),(390,844),(768,1024),(1024,768)]:
        page.set_viewport_size({'width':vw_,'height':vh_});page.wait_for_timeout(300)
        page.locator('#btnPaper').tap();page.wait_for_timeout(300)
        cell=page.locator('#pictureGrid .b').first.bounding_box()
        prev=page.locator('#pictureGrid .preview').first.bounding_box()
        assert cell['height']>=110,(vw_,vh_,'cell',cell)
        assert prev['height']>=80,(vw_,vh_,'preview',prev)
        assert prev['width']>=80,(vw_,vh_,'preview',prev)
        # Still no scrolling, and still at most six cards.
        assert page.evaluate("()=>{const c=document.getElementById('paperCard');"
                             "return c.scrollHeight<=c.clientHeight+1 && c.scrollWidth<=c.clientWidth+1}"),(vw_,vh_)
        n=page.locator('#pictureGrid .b:visible').count()
        assert 0<n<=6,(vw_,vh_,n)
        # The toggle he presses is still reachable over the open gallery.
        assert page.evaluate("""()=>{const b=document.getElementById('btnPaper');
          const r=b.getBoundingClientRect();
          const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
          return hit===b || b.contains(hit);}"""),(vw_,vh_,'toggle covered')
        page.locator('#btnPaper').tap();page.wait_for_timeout(200)
    assert not errors,errors

    # --- Review fixes 2 and 3: the lifted cluster must not strand or mis-size ---
    page=browser.new_page(viewport={'width':1024,'height':768},has_touch=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    page.evaluate("choosePaper({dataset:{paper:'cat'}})");page.wait_for_timeout(400)

    page.locator('#btnPaper').tap();page.wait_for_timeout(300)
    # Nothing measured while the cluster is lifted may mis-size the paper: a
    # relayout with the gallery open must leave the geometry untouched.
    snap=page.evaluate('[vw,vh,viewTop,viewLeft]')
    page.evaluate('sizeLayers()');page.wait_for_timeout(250)
    assert page.evaluate('[vw,vh,viewTop,viewLeft]')==snap,(snap,page.evaluate('[vw,vh,viewTop,viewLeft]'))
    # The drawing area still starts below the cluster, not below a short top row.
    assert page.evaluate("""()=>{const o=window.visualViewport?visualViewport.offsetTop:0;
      return drawingBounds().y >= document.getElementById('actions').getBoundingClientRect().bottom - o - 0.5;}""")
    # Rotating with the gallery open keeps the toggle on screen and tappable.
    page.set_viewport_size({'width':768,'height':1024});page.wait_for_timeout(450)
    box=page.locator('#btnPaper').bounding_box()
    assert box['x']>=0 and box['x']+box['width']<=768.5,box
    assert box['y']>=0 and box['y']+box['height']<=1024.5,box
    assert page.evaluate("""()=>{const b=document.getElementById('btnPaper');
      const r=b.getBoundingClientRect();
      const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
      return hit===b||b.contains(hit);}"""),box
    # Undo and Clean are not live over the open gallery: he mashes exactly there,
    # and neither shows him anything when the gallery is covering the paper.
    assert page.locator('#btnUndo').is_disabled()
    assert page.locator('#btnNew').is_disabled()
    page.locator('#btnPaper').tap();page.wait_for_timeout(300)
    assert page.locator('#paperSheet').is_hidden()
    # Closing restores them, and the cluster goes back into the top row.
    assert page.evaluate("document.getElementById('actions').parentElement.id")=='topRow'
    assert page.locator('#btnNew').is_disabled()==False
    assert not errors,errors

    # --- Colouring is free by default: nothing clips a stroke to a shape ---
    page=browser.new_page(viewport={'width':1280,'height':900})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate("localStorage.removeItem('artstudio-settings')")
    page.reload();page.wait_for_timeout(450)
    try:
        page.click('#setupDone',timeout=2000)
    except Exception:
        pass
    page.evaluate('soundOn=false')
    assert page.evaluate('settings.helper')==False,page.evaluate('settings.helper')
    assert 'off' in page.evaluate("document.querySelector('#gHelper .cap').textContent")

    def fworld(u,v):
        return page.evaluate('([u,v])=>{const s=Math.min(designWidth,designHeight)*.82;return [vw/2+(u-50)*s/100,vh/2+(v-50)*s/100]}',[u,v])
    def fscreen(x,y):
        r=page.locator('#hit').bounding_box();scale,left,top=page.evaluate('[viewScale,viewLeft,viewTop]')
        return r['x']+left+x*scale,r['y']+top+y*scale
    def falpha(x,y):return page.evaluate('([x,y])=>actx.getImageData(Math.floor(x*dpr),Math.floor(y*dpr),1,1).data[3]',[x,y])

    # The same butterfly stroke the opt-in check uses, now expected to run free.
    page.evaluate("setTool('marker');setColor('#1e88e5')");page.wait_for_timeout(400)
    inside,outside=fworld(31,27),fworld(25,6)
    page.mouse.move(*fscreen(*inside));page.mouse.down()
    page.mouse.move(*fscreen(*outside),steps=30);page.mouse.up();page.wait_for_timeout(250)
    assert falpha(*inside)>0,falpha(*inside)
    assert falpha(*outside)>0,falpha(*outside)

    # A value stored by an older build must not keep clipping him.
    page.evaluate("()=>{localStorage.setItem('artstudio-settings',JSON.stringify({helper:true,music:true,stars:0}))}")
    page.reload();page.wait_for_timeout(450)
    try:
        page.click('#setupDone',timeout=2000)
    except Exception:
        pass
    assert page.evaluate('settings.helper')==False,page.evaluate('settings.helper')

    # The grown-up toggle still turns it back on, and that choice sticks.
    page.evaluate('soundOn=false')
    page.evaluate("openSheet('grownSheet')");page.click('#gHelper');page.wait_for_timeout(150)
    assert page.evaluate('settings.helper')==True
    page.reload();page.wait_for_timeout(450)
    try:
        page.click('#setupDone',timeout=2000)
    except Exception:
        pass
    assert page.evaluate('settings.helper')==True,page.evaluate('settings.helper')
    assert not errors,errors
    browser.close()
    print('PASS: instant taps, cards honoured at once, no post-pick scribbles, Next advances per tap, strokes stay in shapes, tracing earns stars, tap engine fires once per gesture, two-finger taps, ambiguous gaps refused')
