"""Rainbow should retain bright color during continuous and repeated scribbling."""
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1366,'height':900})
    page.goto((Path(__file__).resolve().parents[1]/'write_v5.html').as_uri())
    page.click('#setupDone')
    page.evaluate("choosePaper({dataset:{paper:'white'}});setTool('rainbow');soundOn=false")
    def point(x,y):
        return page.evaluate('([x,y])=>[viewLeft+x*viewScale,viewTop+y*viewScale]',[x,y])
    def brightness(canvas):
        return page.evaluate('''name=>{const a=window[name].getContext('2d').getImageData(490*dpr,395*dpr,20*dpr,10*dpr).data;
          let light=0,count=0;for(let i=0;i<a.length;i+=4){if(a[i+3]>100){light+=a[i]+a[i+1]+a[i+2];count++;}}
          return count?light/count:0;}''',canvas)
    # Uninterrupted scribbling and many separate strokes both used to multiply dark.
    for stroke_index in range(8):
        page.mouse.move(*point(350,400));page.mouse.down()
        for i in range(6):page.mouse.move(*point(650 if i%2==0 else 350,400),steps=16)
        page.wait_for_timeout(25)
        assert brightness('live')>400,(stroke_index,brightness('live'))
        page.mouse.up()
        assert brightness('art')>400,(stroke_index,brightness('art'))
    print('PASS: Rainbow stays bright through 48 repeated passes, both live and committed')
    browser.close()
