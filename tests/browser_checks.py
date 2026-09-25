"""Optional regression suite. Requires Python Playwright and installed Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright
URL=(Path(__file__).resolve().parents[1]/'write_v5.html').as_uri()
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1280,'height':900},accept_downloads=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(200)
    page.evaluate('soundOn=false')
    def world(x,y):
        r=page.locator('#hit').bounding_box();scale,left,top=page.evaluate('[viewScale,viewLeft,viewTop]')
        return r['x']+left+x*scale,r['y']+top+y*scale
    def tap(x,y):page.mouse.click(*world(x,y))
    def pixel(x,y,canvas='actx'):
        return page.evaluate(f'([x,y])=>Array.from({canvas}.getImageData(Math.floor(x*dpr),Math.floor(y*dpr),1,1).data)',[x,y])
    def select_paper(id,category):
        page.click('#btnPaper');page.click(f'[data-category="{category}"]')
        for _ in range(30):
            if page.locator(f'[data-paper="{id}"]').count():
                page.click(f'[data-paper="{id}"]');return
            assert not page.locator('#paperNext').is_disabled(),id
            page.click('#paperNext')
        raise AssertionError(id)
    def choose_tool(key):
        if page.evaluate('phoneLayout()'):page.click('#phoneTools')
        page.click(f'[data-tool="{key}"]')
    def choose_color(color):
        if page.evaluate('phoneLayout()'):page.click('#phoneColors')
        page.click(f'[data-color="{color}"]')
    assert page.evaluate('tool')=='crayon'
    choose_tool('fill')
    assert page.evaluate('TRACING.length')==24
    # Fullscreen-sized paper, including previously unused margins.
    r=page.locator('#page').bounding_box()
    assert r['x']==0 and r['y']==0 and r['width']==1280 and r['height']==900,r
    x,y=page.evaluate('[vw/2-19*Math.min(designWidth,designHeight)*.82/100,vh/2-12*Math.min(designWidth,designHeight)*.82/100]')
    tap(x,y);assert pixel(x,y)==[229,57,53,255]
    assert pixel(5,5)[3]==0
    choose_color('#1e88e5');tap(x,y);assert pixel(x,y)==[30,136,229,255]
    page.click('#btnUndo');assert pixel(x,y)==[229,57,53,255]
    page.click('#btnRedo');assert pixel(x,y)==[30,136,229,255]
    # Clicking any printed line does nothing and does not create an undo step.
    outline=page.evaluate('(()=>{const i=guidePixels.findIndex(v=>v>200);return [(i%art.width)/dpr,Math.floor(i/art.width)/dpr]})()')
    before=page.evaluate('art.toDataURL()');page.evaluate('([x,y])=>bucketFill(x,y,"#e53935")',outline)
    assert page.evaluate('art.toDataURL()')==before
    select_paper('turtle','picture');assert pixel(x,y)[3]==0
    page.click('#btnUndo');assert page.evaluate('paperId')=='butterfly'
    assert page.evaluate('art.toDataURL()')==before
    page.set_viewport_size({'width':768,'height':1024});page.wait_for_timeout(250)
    assert page.evaluate('Math.abs(art.getBoundingClientRect().width/vw-art.getBoundingClientRect().height/vh)<.00005')
    # Marker revisits within one uninterrupted stroke must darken the crossing.
    page.set_viewport_size({'width':1280,'height':900});page.wait_for_timeout(250)
    select_paper('white','plain');choose_tool('marker');choose_color('#1e88e5')
    page.mouse.move(*world(280,350));page.mouse.down();page.mouse.move(*world(720,350),steps=75);page.wait_for_timeout(40)
    first=pixel(500,350,'lctx')
    page.mouse.move(*world(720,500),steps=30);page.mouse.move(*world(500,500),steps=40);page.mouse.move(*world(500,220),steps=50);page.wait_for_timeout(40)
    crossed=pixel(500,350,'lctx')
    brightness=lambda rgba:sum(v*rgba[3]/255+255-rgba[3] for v in rgba[:3])
    assert brightness(crossed)<brightness(first)-15,(first,crossed)
    preview=page.evaluate('live.toDataURL()');page.mouse.up();assert page.evaluate('art.toDataURL()')==preview
    page.click('#btnUndo');assert pixel(500,350)[3]==0
    page.click('#btnRedo');assert pixel(500,350)==crossed
    # Pigment, coverage, and glow all build during uninterrupted retracing.
    def metrics():
        return page.evaluate('(()=>{const a=lctx.getImageData(450*dpr,335*dpr,100*dpr,30*dpr).data;let ink=0,alpha=0;for(let i=0;i<a.length;i+=4){alpha+=a[i+3];ink+=(765-a[i]-a[i+1]-a[i+2])*a[i+3]/255;}return {ink,alpha};})()')
    for key in ['crayon','pencil','marker','paint','spray','rainbow','neon','glitter','bubbles','stamp']:
        page.evaluate("key=>{freshPage();setColor('#1e88e5');setTool(key);}",key)
        page.mouse.move(*world(300,350));page.mouse.down();page.mouse.move(*world(700,350),steps=45);page.wait_for_timeout(35)
        first=metrics()
        page.mouse.move(*world(300,350),steps=45);page.wait_for_timeout(35);second=metrics();page.mouse.up()
        assert second['alpha']>first['alpha']*1.05,(key,first,second)
        assert second['ink']>first['ink']*1.05,(key,first,second)
    # A pressed stylus accumulates crayon pigment too, without a pen-up event.
    page.evaluate("freshPage();setTool('crayon');")
    cdp=page.context.new_cdp_session(page)
    def pen(kind,x,y,down=True):
        px,py=world(x,y)
        cdp.send('Input.dispatchMouseEvent',{'type':kind,'x':px,'y':py,'button':'left' if kind!='mouseMoved' else 'none','buttons':1 if down else 0,'pointerType':'pen','force':.8 if down else 0})
    pen('mousePressed',300,350)
    assert page.evaluate('stroke.pen')
    for x in range(310,701,10):pen('mouseMoved',x,350)
    page.wait_for_timeout(40);first=metrics()
    for x in range(690,299,-10):pen('mouseMoved',x,350)
    page.wait_for_timeout(40);second=metrics();pen('mouseReleased',300,350,False)
    assert second['ink']>first['ink']*1.1,(first,second)
    # Drawing beneath immutable vector guides never changes the printed paths.
    select_paper('trace-maze-easy','trace')
    guide_before=page.evaluate('document.getElementById("outlines").toDataURL()')
    for key in page.evaluate('TOOL_ORDER'):
        choose_tool(key)
        page.mouse.move(*world(260,300));page.mouse.down();page.mouse.move(*world(740,450),steps=10);page.mouse.up()
        assert page.evaluate('document.getElementById("outlines").toDataURL()')==guide_before,key
    # Fill reaches beneath smooth antialiased outlines: no erased white fringe.
    select_paper('pattern-rings','pattern')
    center=page.evaluate('(()=>{const s=Math.min(designWidth,designHeight)*.82;return [vw/2-.24*s,vh/2-.24*s]})()')
    page.evaluate('([x,y])=>bucketFill(x,y,"#1e88e5")',center)
    edge=page.evaluate('''(()=>{
      const a=actx.getImageData(0,0,art.width,art.height).data,w=art.width;let tested=0,holes=0;
      for(let i=w;i<guidePixels.length-w;i++)if(guidePixels[i]>0&&guidePixels[i]<255){
        if([i-1,i+1,i-w,i+w].some(j=>!guidePixels[j]&&a[j*4+3]===255)){
          tested++;if(a[i*4+3]!==255)holes++;
        }
      }return {tested,holes};
    })()''')
    assert edge['tested']>10 and edge['holes']==0,edge
    cx,cy=world(*center);page.screenshot(path='/tmp/filled-outline.png',clip={'x':cx-80,'y':cy-80,'width':160,'height':160})
    # Separate honeycomb cells stay separate and are repeatedly recolorable.
    select_paper('pattern-honeycomb','pattern')
    page.evaluate("(()=>{const s=Math.min(designWidth,designHeight)*.82;bucketFill(vw/2+(12-50)*s/100,vh/2+(11-50)*s/100,'#e53935');})()")
    assert page.evaluate("(()=>{const s=Math.min(designWidth,designHeight)*.82;return actx.getImageData((vw/2+(25.5-50)*s/100)*dpr,(vh/2+(11+Math.sqrt(3)*4.5-50)*s/100)*dpr,1,1).data[3]===0;})()")
    # Pale dotted tracing outlines must also reject bucket taps.
    select_paper('trace-ABC','trace')
    assert page.evaluate('(()=>{const i=guidePixels.findIndex(v=>v>200);const old=art.toDataURL();bucketFill((i%art.width)/dpr,Math.floor(i/art.width)/dpr,"#e53935");return art.toDataURL()===old;})()')
    # Generated pages and custom words round-trip through history and storage.
    page.click('#btnPaper');page.click('[data-category="picture"]');page.click('#surprise');seed=page.evaluate('pageSeed')
    page.click('#btnUndo');page.click('#btnRedo');assert page.evaluate('pageSeed')==seed
    page.click('#btnPaper');page.click('[data-category="words"]');page.fill('#traceWords','River');page.click('#wordForm button')
    assert page.evaluate('traceText')=='River'
    page.evaluate('save()');page.reload();page.wait_for_timeout(350)
    assert page.evaluate('paperId')=='trace-name' and page.evaluate('traceText')=='River'
    # All templates render; all controls can be reached with taps in every layout.
    page.evaluate('for(const p of [...PICTURES,...PATTERNS,...TRACING]){paperId=p.id;drawPaper();}paperId="trace-maze-easy";drawPaper();')
    for width,height in [(1280,900),(768,1024),(390,844),(844,390)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(250)
        r=page.locator('#page').bounding_box();assert r['width']==width and r['height']==height,r
        assert page.evaluate('Math.abs(art.getBoundingClientRect().width/vw-art.getBoundingClientRect().height/vh)<.00005')
        assert page.evaluate('document.getElementById("outlines").width===Math.ceil(viewW()*Math.min(3,devicePixelRatio))')
        for key in page.evaluate('TOOL_ORDER'):choose_tool(key)
        for col in page.evaluate('COLORS'):choose_color(col)
        choose_tool('stamp');stamps=set()
        if page.evaluate('phoneLayout()'):page.click('#phoneColors')
        for _ in range(30):
            stamps.update(page.locator('[data-stamp]').evaluate_all('(els)=>els.map(el=>el.dataset.stamp)'))
            if len(stamps)==24:break
            page.click('#moreColors')
        assert len(stamps)==24
        for sel in ['#rail','#bottom','#side']:
            assert page.locator(sel).evaluate('(el)=>el.scrollHeight<=el.clientHeight+2 && el.scrollWidth<=el.clientWidth+2'),(width,height,sel)
        page.evaluate('closeSheets()')
        page.click('#btnPaper')
        for category,expected in [('plain',7),('picture',31),('pattern',10),('trace',24)]:
            page.click(f'[data-category="{category}"]');found=set()
            for _ in range(30):
                found.update(page.locator('[data-paper]').evaluate_all('(els)=>els.map(el=>el.dataset.paper)'))
                assert page.locator('#paperCard').evaluate('(el)=>el.scrollHeight<=el.clientHeight+2 && el.scrollWidth<=el.clientWidth+2'),(width,height,category)
                for control in ['#paperNext','#paperPrev','#paperTabs','#paperSheet .closeSheet']:
                    box=page.locator(control).bounding_box();assert box['x']>=0 and box['x']+box['width']<=width and box['y']>=0 and box['y']+box['height']<=height,(width,height,control,box)
                if page.locator('#paperNext').is_disabled():break
                page.click('#paperNext')
            assert len(found)==expected,(category,len(found))
        page.screenshot(path=f'/tmp/picker-{width}.png');page.click('#paperSheet .closeSheet');page.screenshot(path=f'/tmp/canvas-{width}.png')
    # Repeated orientation changes retain marks in newly exposed workspace margins.
    page.set_viewport_size({'width':1280,'height':900});page.wait_for_timeout(250)
    select_paper('white','plain')
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250)
    point=page.evaluate('[vw/2,vh/2-designHeight/2-60]')
    page.evaluate("setTool('marker');setColor('#e53935');")
    tap(*point);assert pixel(*point)[3]>0
    for _ in range(3):
        page.set_viewport_size({'width':1280,'height':900});page.wait_for_timeout(220)
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(220)
    point=page.evaluate('[vw/2,vh/2-designHeight/2-60]')
    assert pixel(*point)[3]>0
    # Parent hold and PNG export.
    page.set_viewport_size({'width':1280,'height':900});page.wait_for_timeout(200)
    r=page.locator('#grown').bounding_box();page.mouse.move(r['x']+20,r['y']+20);page.mouse.down();page.wait_for_timeout(1400)
    assert not page.locator('#grownSheet').is_visible()
    page.wait_for_timeout(1750);page.mouse.up();assert page.locator('#grownSheet').is_visible()
    with page.expect_download() as d:page.click('#gSave')
    assert d.value.suggested_filename.endswith('.png')
    assert not errors,errors
    # Actual touch input, offline.
    context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,offline=True)
    touch=context.new_page();touch.goto(URL);touch.locator('#setupDone').tap();touch.wait_for_timeout(200)
    for key in touch.evaluate('TOOL_ORDER'):
        touch.locator('#phoneTools').tap()
        assert touch.locator('#rail .tool:visible').count()==12
        touch.locator(f'[data-tool="{key}"]').tap()
        assert touch.evaluate('tool')==key
    touch.locator('#btnPaper').tap();touch.locator('[data-category="trace"]').tap();touch.locator('#paperNext').tap()
    assert touch.locator('#paperCard').evaluate('(el)=>el.scrollHeight<=el.clientHeight+2')
    context.close()
    # Retina vectors and previews use adequate backing resolution and preserve circles.
    retina=browser.new_context(viewport={'width':1024,'height':768},device_scale_factor=2)
    rp=retina.new_page();rp.goto(URL);rp.click('#setupDone');rp.wait_for_timeout(200)
    assert rp.evaluate('document.getElementById("outlines").width')==2048
    rp.evaluate("choosePaper({dataset:{paper:'pattern-rings'}})")
    for w,h in [(1024,768),(390,844),(844,390),(1024,768)]:
        rp.set_viewport_size({'width':w,'height':h});rp.wait_for_timeout(250)
        assert rp.evaluate('Math.abs(art.getBoundingClientRect().width/vw-art.getBoundingClientRect().height/vh)<.00005')
        assert rp.evaluate('document.getElementById("outlines").width')==w*2
        assert rp.evaluate('document.getElementById("outlines").height')==h*2
        circle=rp.evaluate('''(()=>{
          const cv=document.getElementById('outlines'),ctx=cv.getContext('2d'),s=Math.min(designWidth,designHeight)*.82;
          const ratio=cv.width/viewW(),cx=(viewLeft+(vw/2-.24*s)*viewScale)*ratio,cy=(viewTop+(vh/2-.24*s)*viewScale)*ratio,r=.21*s*viewScale*ratio;
          const x0=Math.floor(cx-r-8),y0=Math.floor(cy-r-8),n=Math.ceil(r*2+16);
          const row=ctx.getImageData(x0,Math.round(cy),n,1).data,col=ctx.getImageData(Math.round(cx),y0,1,n).data;
          const span=a=>{let first=-1,last=-1;for(let i=0;i<n;i++)if(a[i*4+3]>100){if(first<0)first=i;last=i;}return last-first;};
          return {x:span(row),y:span(col)};
        })()''')
        assert abs(circle['x']-circle['y'])<=2,circle
    rp.click('#btnPaper');rp.click('[data-category="pattern"]')
    assert rp.locator('.preview').first.evaluate('(c)=>c.width')==384
    rp.screenshot(path='/tmp/patterns-retina.png')
    retina.close();browser.close()
    print('PASS: all 10 drawing tools accumulate within a stroke; pressed-pen crayon; smooth protected guides without white fringes; enclosed pattern fills; uniform scaling and retained margins; native Retina vectors; undo/save/export; every tool/template via taps; offline touch and four layouts')
