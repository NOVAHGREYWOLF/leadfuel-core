#!/usr/bin/env python3
"""Builds the Lava Cap Historical Landmark static site into dist/ (Hostinger-ready).

Content is taken from the live lavacapmine.com (Oct 2, 2026) with the audit fixes applied.
Anything still needed from Misty is wrapped in <span class="tc">...</span> (shows as a gold
"TO CONFIRM" chip on the temp site) and listed in NEEDS_FROM_MISTY.md.

Usage: python3 build.py [--live]   (--live removes noindex for launch)
"""
import os, shutil, sys, zipfile, html

LIVE = '--live' in sys.argv
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC, DIST = os.path.join(ROOT, 'src'), os.path.join(ROOT, 'dist')
SITE = 'https://lavacapmine.com'
EMAIL = 'admin@lavacapmine.com'
PAYPAL = 'https://www.paypal.com/donate/?hosted_button_id=59MP7WRZTS2VW'
SOCIAL = [('Facebook', 'https://www.facebook.com/lavacapgoldmine/'),
          ('Instagram', 'https://www.instagram.com/lavacapmine'),
          ('YouTube', 'https://www.youtube.com/@LavaCapGoldMine'),
          ('X', 'https://x.com/Lavacapmine'),
          ('Twitch', 'https://www.twitch.tv/lavacapgoldmine')]


def tc(text):
    return f'<span class="tc" title="Misty to confirm">{text}</span>'


NAV = [('index.html', 'Home'), ('history.html', 'History'), ('education.html', 'Education'),
       ('visit.html', 'Visit'), ('donate.html', 'Donate'), ('blog.html', 'Stories'), ('contact.html', 'Contact')]

CSS = """
:root{--bg:#14110d;--bg2:#1c1812;--card:#221d15;--line:#3d3328;--gold:#c9a84c;--gold2:#e2c675;--ink:#f2ece0;--mute:#b8ad98;--max:1120px}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
img{max-width:100%;display:block}a{color:var(--gold2)}a:hover{color:#fff}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif;font-weight:700;line-height:1.2;margin:0 0 .5em}
h1{font-size:clamp(2.2rem,5.5vw,3.8rem)}h2{font-size:clamp(1.6rem,3.4vw,2.3rem)}h3{font-size:1.2rem}
p{margin:0 0 1em}.wrap{max-width:var(--max);margin:0 auto;padding:0 20px}
.eyebrow{color:var(--gold);letter-spacing:.18em;text-transform:uppercase;font-size:.78rem;font-weight:600;margin-bottom:.8rem}
.mute{color:var(--mute)}
header.top{position:sticky;top:0;z-index:20;background:rgba(20,17,13,.95);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:72px}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink);font-family:Georgia,serif;font-weight:700}
.brand img{height:52px;width:52px;border-radius:6px;object-fit:cover}.brand span{font-size:1.05rem;line-height:1.15}
nav ul{display:flex;gap:4px;list-style:none;margin:0;padding:0}
nav a{display:block;padding:10px 12px;color:var(--ink);text-decoration:none;font-size:.95rem;border-radius:6px}
nav a:hover,nav a[aria-current]{color:var(--gold2)}nav a[aria-current]{border-bottom:2px solid var(--gold)}
nav .cta{background:var(--gold);color:#1a1409;font-weight:600}nav .cta:hover,nav .cta[aria-current]{background:var(--gold2);color:#1a1409;border-bottom:0}
.menu-btn{display:none;background:none;border:1px solid var(--line);color:var(--ink);padding:8px 12px;border-radius:6px;font-size:1rem}
@media(max-width:900px){.menu-btn{display:block}nav{display:none;position:absolute;left:0;right:0;top:72px;background:var(--bg);border-bottom:1px solid var(--line)}
nav.open{display:block}nav ul{flex-direction:column;padding:10px 20px 16px}nav a{padding:12px 4px}}
.banner{background:var(--gold);color:#1a1409;text-align:center;padding:9px 16px;font-weight:600;font-size:.95rem}
.hero{position:relative;min-height:78vh;display:flex;align-items:flex-end;background:#000 center/cover}
.hero.sm{min-height:48vh}.hero::before{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,17,13,.35),rgba(20,17,13,.88))}
.hero .wrap{position:relative;width:100%;padding-top:80px;padding-bottom:56px}.hero p.lead{max-width:680px;font-size:1.15rem;color:#e6dcc8}
.btn{display:inline-block;padding:13px 24px;border-radius:6px;text-decoration:none;font-weight:600;border:1px solid var(--gold);margin:6px 10px 6px 0}
.btn.p{background:var(--gold);color:#1a1409}.btn.p:hover{background:var(--gold2);color:#1a1409}.btn.s{color:var(--gold2)}.btn.s:hover{background:var(--gold);color:#1a1409}
section{padding:72px 0}section.alt{background:var(--bg2);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.grid{display:grid;gap:24px}.g2{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(3,1fr)}.g4{grid-template-columns:repeat(4,1fr)}
@media(max-width:900px){.g3,.g4{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){.g2,.g3,.g4{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}.card .pad{padding:22px}
.card img{width:100%;height:220px;object-fit:cover}.card ul{padding-left:18px;margin:.4em 0 0;color:var(--mute);font-size:.95rem}
.split{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center}@media(max-width:820px){.split{grid-template-columns:1fr;gap:28px}}
.split img{border-radius:10px;border:1px solid var(--line);width:100%;max-height:520px;object-fit:cover}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}
@media(max-width:700px){.stats{grid-template-columns:repeat(2,1fr)}}.stats div{background:var(--card);padding:22px 14px;text-align:center}
.stats b{display:block;font-family:Georgia,serif;font-size:1.5rem;color:var(--gold2)}.stats span{font-size:.85rem;color:var(--mute)}
.timeline{border-left:2px solid var(--gold);margin-left:8px}.timeline .it{position:relative;padding:0 0 28px 28px}
.timeline .it::before{content:"";position:absolute;left:-8px;top:6px;width:14px;height:14px;border-radius:50%;background:var(--gold)}
.timeline .yr{color:var(--gold2);font-weight:700;letter-spacing:.04em}
table{width:100%;border-collapse:collapse;table-layout:auto}.card,.notice,td,th,p,li{overflow-wrap:anywhere}td,th{padding:12px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{white-space:nowrap;overflow-wrap:normal;color:var(--gold);font-size:.8rem;letter-spacing:.1em;text-transform:uppercase}
.tier h3{margin-bottom:.1em}.tier .amt{color:var(--gold2);font-family:Georgia,serif;font-size:1.5rem;margin-bottom:.6em}
.notice{border:1px solid var(--gold);border-radius:10px;padding:22px 24px;background:rgba(201,168,76,.07)}
.tc{background:var(--gold);color:#1a1409;padding:0 6px;border-radius:4px;font-size:.88em;font-weight:600;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.tc::after{content:" · TO CONFIRM";font-size:.7em;letter-spacing:.05em}
form label{display:block;font-size:.9rem;margin:14px 0 4px;color:var(--mute)}
input,select,textarea{width:100%;padding:12px;border-radius:6px;border:1px solid var(--line);background:var(--bg2);color:var(--ink);font:inherit}
textarea{min-height:140px}.hp{position:absolute;left:-9999px}
footer{background:#0e0c09;border-top:1px solid var(--line);padding:56px 0 28px;font-size:.93rem;color:var(--mute)}
footer h4{color:var(--ink);margin:0 0 .6em;font-family:Georgia,serif}footer ul{list-style:none;padding:0;margin:0}footer li{margin:.35em 0}
footer a{color:var(--mute);text-decoration:none}footer a:hover{color:var(--gold2)}.fine{border-top:1px solid var(--line);margin-top:32px;padding-top:18px;font-size:.82rem}
.skip{position:absolute;left:-9999px}.skip:focus{left:10px;top:10px;background:#fff;color:#000;padding:8px;z-index:50}
:focus-visible{outline:2px solid var(--gold2);outline-offset:2px}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

JS = """document.querySelector('.menu-btn').addEventListener('click',function(){var n=document.getElementById('nav');var o=n.classList.toggle('open');this.setAttribute('aria-expanded',o)});"""


def page(fname, title, desc, body, hero=None, active=None):
    robots = '' if LIVE else '<meta name="robots" content="noindex,nofollow">'
    def navitem(h, n):
        cur = ' aria-current="page"' if h == fname else ''
        cls = ' class="cta"' if h == 'donate.html' else ''
        return f'<li><a href="{h}"{cur}{cls}>{n}</a></li>'
    nav = ''.join(navitem(h, n) for h, n in NAV)
    heroh = ''
    if hero:
        img, eyebrow, h1, lead, small = hero[:5]
        ctas = hero[5] if len(hero) > 5 else ''
        heroh = (f'<div class="hero{" sm" if small else ""}" style="background-image:url(images/{img})"><div class="wrap">'
                 f'<div class="eyebrow">{eyebrow}</div><h1>{h1}</h1><p class="lead">{lead}</p>{ctas}</div></div>')
    soc = ''.join(f'<li><a href="{u}" rel="noopener" target="_blank">{n}</a></li>' for n, u in SOCIAL)
    ld = ('{"@context":"https://schema.org","@type":"NGO","name":"Lava Cap Historical Landmark",'
          f'"url":"{SITE}","email":"{EMAIL}","logo":"{SITE}/images/logo.jpg",'
          '"description":"A 501(c)(3) non-profit preserving the Lava Cap Gold Mine near Nevada City, California.",'
          '"address":{"@type":"PostalAddress","addressLocality":"Nevada City","addressRegion":"CA","postalCode":"95959","addressCountry":"US"},'
          '"sameAs":[' + ','.join(f'"{u}"' for _, u in SOCIAL) + ']}')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc)}">{robots}
<link rel="canonical" href="{SITE}/{'' if fname=='index.html' else fname}">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{SITE}/{'' if fname=='index.html' else fname}">
<meta property="og:image" content="{SITE}/images/pages-home-hero.jpg"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="images/favicon.png"><link rel="stylesheet" href="style.css">
<script type="application/ld+json">{ld}</script></head><body>
<a class="skip" href="#main">Skip to content</a>
{'' if LIVE else '<div class="banner">TEMPORARY PREVIEW for review. Gold <b>TO CONFIRM</b> tags mark details we still need from you. Not public.</div>'}
<header class="top"><div class="wrap bar"><a class="brand" href="index.html"><img src="images/logo.jpg" alt="Lava Cap Gold Mine Historical District seal"><span>Lava Cap<br>Historical Landmark</span></a>
<button class="menu-btn" aria-expanded="false" aria-controls="nav">Menu</button>
<nav id="nav" aria-label="Main"><ul>{nav}</ul></nav></div></header>
{heroh}<main id="main">{body}</main>
<footer><div class="wrap"><div class="grid g4"><div><h4>Lava Cap Historical Landmark</h4><p>A 501(c)(3) non-profit preserving the Lava Cap Gold Mine near Nevada City, California.</p></div>
<div><h4>Explore</h4><ul>{''.join(f'<li><a href="{h}">{n}</a></li>' for h,n in NAV)}</ul></div>
<div><h4>Contact</h4><ul><li><a href="mailto:{EMAIL}">{EMAIL}</a></li><li>Nevada City, CA 95959</li><li>{tc('Phone number')}</li><li>{tc('Mailing address')}</li></ul></div>
<div><h4>Follow</h4><ul>{soc}</ul></div></div>
<div class="fine">&copy; 2026 Lava Cap Historical Landmark. All rights reserved. &nbsp;|&nbsp; <a href="privacy.html">Privacy</a> &nbsp;|&nbsp; <a href="terms.html">Terms</a> &nbsp;|&nbsp; Site by <a href="https://etg.ai">Emerging Technology Group</a></div></div></footer>
<script>{JS}</script></body></html>"""


def pages():
    P = {}
    # ---------- HOME ----------
    P['index.html'] = page('index.html', 'Lava Cap Historical Landmark | Preserving California\'s Golden Legacy',
        'The Lava Cap Gold Mine is being transformed into a living historical landmark and educational center near Nevada City, CA. Opening spring 2027.',
        f"""<section><div class="wrap"><div class="stats"><div><b>Est. 1861</b><span>Mine established</span></div><div><b>Nevada City, CA</b><span>Location</span></div><div><b>Spring 2027</b><span>Opening to visitors</span></div><div><b>501(c)(3)</b><span>Non-profit</span></div></div></div></section>
<section class="alt"><div class="wrap split"><div><div class="eyebrow">Our Mission</div><h2>From Mine to Monument</h2>
<p>Deep in the Sierra Nevada foothills, the Lava Cap Gold Mine stands as one of California's most significant Gold Rush-era sites. For decades it lay dormant, its tunnels silent and its stories untold.</p>
<p>Today, a dedicated community of historians, educators and preservationists is breathing new life into this landmark. We are transforming the Lava Cap mine into a historical site, educational center and living museum, so the stories of the miners, the era and the land are never forgotten.</p>
<a class="btn p" href="history.html">Learn Our Story</a></div><img src="images/pages-home-mission.jpg" alt="Concept view of the planned welcome building" loading="lazy"></div></section>
<section><div class="wrap"><div class="eyebrow">What We Do</div><h2>Experience Living History</h2><div class="grid g4">
<div class="card"><img src="images/pages-home-tours.jpg" alt="Historic mine adit with blue rock" loading="lazy"><div class="pad"><h3>Historical Tours</h3><p class="mute">Walk the same ground as the miners of the 1930s, with authentic artifacts, restored structures and expert storytelling. Starting spring 2027.</p></div></div>
<div class="card"><img src="images/pages-home-education.jpg" alt="Visitors inside the historic mill" loading="lazy"><div class="pad"><h3>Educational Programs</h3><p class="mute">K-12 field trips and university research partnerships connect people with California's mining heritage.</p></div></div>
<div class="card"><img src="images/pages-history-equipment.jpg" alt="Historic ore cart in the forest" loading="lazy"><div class="pad"><h3>Preservation</h3><p class="mute">Our team of historians and conservationists works to restore and protect the original structures, equipment and archives.</p></div></div>
<div class="card"><img src="images/pages-home-community.jpg" alt="Portable sawmill milling a log" loading="lazy"><div class="pad"><h3>Community</h3><p class="mute">Workshops, volunteer days and living history demonstrations that bring neighbors together.</p></div></div></div></div></section>
<section class="alt"><div class="wrap" style="text-align:center;max-width:760px"><h2>Help Us Preserve History for Future Generations</h2>
<p class="mute">Every dollar donated goes toward restoring the Lava Cap mine, developing educational programs and making sure this piece of California history endures.</p>
<a class="btn p" href="{PAYPAL}" target="_blank" rel="noopener">Donate Now</a><a class="btn s" href="donate.html">Ways to Support</a></div></section>""",
        hero=('pages-home-hero.jpg', 'Nevada City, California', 'Preserving California\'s Golden Legacy',
              'The Lava Cap Gold Mine, once one of Nevada County\'s most productive mines, is being transformed into a living historical landmark and educational center. Opening to visitors in spring 2027.',
              False, '<a class="btn p" href="history.html">Explore the History</a><a class="btn s" href="donate.html">Support Our Mission</a>'))

    # ---------- HISTORY ----------
    tl = [
        ('1861', 'Lava Cap Mine Established', 'The Lava Cap Mine began active operations in 1861, following the discovery of its quartz vein system around 1860. After an inactive period from 1918 to the early 1930s, the site was reorganized as the Lava Cap Gold Mining Corporation in 1932 and 1933 and became a major hard-rock operation during the Great Depression.'),
        ('1933', 'Gold Revaluation Spurs Growth', 'The Gold Reserve Act raised the official price of gold from $20.67 to $35 per ounce. Previously marginal ore became profitable and the mine expanded rapidly.'),
        ('1935 to 1941', 'Peak Production Years', 'About 300 miners worked around the clock, bussed in daily from Nevada City, on wages that made Lava Cap a lifeline during the Depression. The operation included a stamp mill, an assay office and worker housing. For every ounce of gold, the mine yielded roughly ten ounces of silver. ' + tc('Silver ranking claim: Misty to source')),
        ('1936', 'European Flotation System Installed', 'A flotation system imported from Europe was installed to improve recovery by separating gold-bearing minerals from crushed ore. ' + tc('Recovery figure: the old site said "300 ounces of gold per ton", which looks like a typo')),
        ('1938', 'Infrastructure at Its Height', 'The complex reached its fullest extent, with multiple shaft levels, a processing plant, a company store and a community of families living on the property.'),
        ('1942', 'Wartime Closure', 'War Production Board Order L-208 shut down non-essential gold mining in the United States. Lava Cap\'s tungsten production, a critical war material, earned a one-year exemption. When it expired, the tunnels went dark.'),
        ('1945 to 1980s', 'Dormant Decades', 'Attempts to reopen the mine after the war proved economically challenging. The site passed through several owners as the structures weathered.'),
        ('1990s', 'Historic Recognition', 'Growing interest in California\'s mining heritage brought renewed attention. Local historians and preservationists began documenting the site, recognizing it as one of the few largely intact hard-rock gold mining complexes in the state.'),
        ('2020s', 'A New Chapter Begins', 'A group of historians, preservationists and community members united to save the mine and turn it into a living historical landmark for all Californians.'),
    ]
    tlh = ''.join(f'<div class="it"><div class="yr">{y}</div><h3>{t}</h3><p class="mute">{b}</p></div>' for y, t, b in tl)
    P['history.html'] = page('history.html', 'History & Heritage | Lava Cap Historical Landmark',
        'Explore the history of the Lava Cap Gold Mine near Nevada City, from its 1861 start through Depression-era peak production to its transformation into a historical landmark.',
        f"""<section><div class="wrap split"><div><div class="eyebrow">The Mine That Shaped a Region</div><h2>One of California's most productive hard-rock mines</h2>
<p>Nestled in the Sierra Nevada foothills near Nevada City, the Lava Cap Gold Mine was one of the most productive hard-rock gold mines in California during the 1930s and 1940s. At its peak, 300 miners worked around the clock, bussed in daily from Nevada City.</p>
<p>Named for the ancient volcanic lava cap that formed the geological conditions for gold deposits, the mine operated through the Great Depression and provided steady work when few other opportunities existed.</p></div>
<img src="images/pages-history-landscape.jpg" alt="Lava Cap headframe tower among the pines" loading="lazy"></div></section>
<section class="alt"><div class="wrap" style="max-width:820px"><div class="eyebrow">Timeline</div><h2>A Century Beneath the Mountain</h2><div class="timeline">{tlh}</div></div></section>
<section><div class="wrap"><div class="eyebrow">Why This Mine Matters</div><h2>A window into the lives of those who built California</h2>
<p class="mute" style="max-width:760px">Lava Cap is more than a collection of old tunnels and rusting machinery. It is a window into the lives of the immigrants, laborers, engineers and dreamers who left their mark on this land.</p>
<div class="stats"><div><b>300</b><span>Miners at peak</span></div><div><b>24/7</b><span>Round-the-clock operation</span></div><div><b>16+ acres</b><span>Historic district</span></div><div><b>Est. 1861</b><span>Mine established</span></div></div></div></section>""",
        hero=('pages-history-hero.jpg', 'History & Heritage', 'A Century Beneath the Mountain',
              'The story of the Lava Cap Gold Mine is the story of California itself: ambition, labor and the pursuit of something precious buried deep in the earth.', True))

    # ---------- EDUCATION ----------
    progs = [
        ('pages-education-fieldtrip.jpg', 'Door detail at the historic mill', 'K-12 Field Trips', 'Grades K-12 · Half or full day',
         'Curriculum-aligned guided tours of the historic mine site. Students explore original structures, handle replica artifacts and hear the stories of the miners. Programs are tailored to grade level and California history standards.',
         ['Guided site tours', 'Hands-on artifact handling', 'Pre- and post-visit materials']),
        ('pages-education-workshop.jpg', 'Beekeeper holding a honeycomb frame', 'Beekeeping Workshop', 'All ages · Half day',
         'Discover the world of bees in the heart of Gold Country: hive management, the role of pollinators and the history of beekeeping in the Sierra Nevada foothills.',
         ['Hands-on hive experience', 'Protective gear provided', 'Honey tasting']),
        ('pages-history-hero.jpg', 'Timber framing inside the old mill', 'University Research Access', 'College and graduate students · By appointment',
         'The Lava Cap site and archives are a resource for research in California history, geology, labor history and environmental studies. We welcome partnerships with universities and research institutions.',
         ['Access to historical archives', 'Faculty partnership program', 'Thesis support']),
        ('pages-home-community.jpg', 'Portable sawmill', 'Wood Skills Workshop', 'Adults and teens 16+ · Full day',
         'A hands-on introduction to working with wood from forest to finished product, including chainsaw operation and safety, portable-mill wood milling, log splitting and tool care.',
         ['Chainsaw operation and safety', 'Wood milling with a portable mill', 'All safety gear provided']),
    ]
    pc = ''.join(f'<div class="card"><img src="images/{i}" alt="{a}" loading="lazy"><div class="pad"><div class="eyebrow">{au}</div><h3>{t}</h3><p class="mute">{d}</p><ul>{"".join(f"<li>{x}</li>" for x in hl)}</ul></div></div>'
                 for i, a, t, au, d, hl in progs)
    P['education.html'] = page('education.html', 'Educational Programs | Lava Cap Historical Landmark',
        'K-12 field trips, beekeeping and wood skills workshops, and university research access at the Lava Cap Historical Landmark in Nevada City, CA. Programs begin in 2027.',
        f"""<section><div class="wrap"><div class="notice"><b>Programs begin in 2027.</b> Field trips and workshops open with the site. Request a booking now and we will contact you when dates are set. {tc('Program availability and any free offer for Title I schools')}</div></div></section>
<section><div class="wrap"><div class="eyebrow">Learning That Lasts a Lifetime</div><h2>Something for every learner</h2>
<p class="mute" style="max-width:760px">There is no better classroom than the real thing. At Lava Cap, students do not just read about history, they walk through it.</p><div class="grid g2">{pc}</div></div></section>
<section class="alt"><div class="wrap" style="text-align:center;max-width:760px"><h2>Book a Program for Your Group</h2><p class="mute">Teachers planning a field trip, professors seeking research access and community members eager to learn are all welcome.</p>
<a class="btn p" href="contact.html">Request a Booking</a></div></section>""",
        hero=('pages-education-hero.jpg', 'Educational Programs', 'History You Can Touch',
              'From K-12 field trips to university research partnerships, Lava Cap brings California\'s Gold Rush era to life through hands-on, curriculum-aligned learning.', True))

    # ---------- VISIT ----------
    P['visit.html'] = page('visit.html', 'Visit | Lava Cap Historical Landmark',
        'Plan your visit to the Lava Cap Historical Landmark in Nevada City, CA. Opening to visitors in spring 2027. Directions, tours, accessibility and site safety information.',
        f"""<section><div class="wrap"><div class="notice"><b>Opening to visitors in spring 2027.</b> Hours, admission and tour dates will be posted here before we open. Follow us on social media for updates.</div></div></section>
<section><div class="wrap grid g2"><div><div class="eyebrow">Hours &amp; Admission</div><h2>Planning your visit</h2>
<table><tr><th>Hours</th><td>{tc('Hours to be announced before opening')}</td></tr><tr><th>Admission</th><td>{tc('Pricing to be announced')}</td></tr><tr><th>Groups</th><td>Private group tours (10 or more) by appointment. <a href="contact.html">Contact us</a>.</td></tr></table></div>
<div><div class="eyebrow">Getting Here</div><h2>Nevada City, CA 95959</h2><p>Located in the Sierra Nevada foothills about 60 miles northeast of Sacramento. Take Highway 49 north to Nevada City.</p>
<p>{tc('Street address or meeting point for GPS')}</p><p>{tc('Parking details')}</p></div></div></section>
<section class="alt"><div class="wrap"><div class="eyebrow">Tours</div><h2>Self-guided and docent-led</h2><div class="grid g3">
<div class="card"><div class="pad"><h3>Self-guided Walking Tour</h3><p class="mute">Included with every visit.</p></div></div>
<div class="card"><div class="pad"><h3>Guided Docent Tour</h3><p class="mute">About 90 minutes. Reservations required. {tc('Days and times')}</p></div></div>
<div class="card"><div class="pad"><h3>Private Group Tour</h3><p class="mute">About 2 hours, for groups of 10 or more, by appointment.</p></div></div></div></div></section>
<section><div class="wrap split"><div><div class="eyebrow">Site Status &amp; Safety</div><h2>The mine and its cleanup</h2>
<p>The Lava Cap Mine property is part of a U.S. Environmental Protection Agency (EPA) Superfund cleanup related to arsenic from historic mine tailings. We believe visitors, teachers and families deserve a plain explanation, so this page will describe which areas are open, what the cleanup involves and what safety guidance applies.</p>
<p>{tc('Misty to supply: current EPA status, areas open to the public, any access rules, and who reviewed this wording')}</p></div>
<img src="images/pages-home-tours.jpg" alt="Historic mine adit and blue rock" loading="lazy"></div></section>
<section class="alt"><div class="wrap" style="max-width:820px"><div class="eyebrow">Accessibility</div><h2>Welcome for all visitors</h2>
<p class="mute">We are committed to making Lava Cap accessible to all visitors. Parts of the historic site involve uneven terrain, so please contact us in advance and we will do our best to accommodate your needs. {tc('Confirm wheelchair access and welcome center details')}</p></div></section>""",
        hero=('pages-home-hero.jpg', 'Visit Us', 'Come See History for Yourself',
              'The Lava Cap Gold Mine Historical Landmark opens to visitors in spring 2027. Check back for details and follow our story.', True))

    # ---------- DONATE ----------
    impact = [('$25', 'Provides digital copies of mine maps'), ('$100', 'Funds one hour of professional historic preservation work'),
              ('$500', 'Restores a section of original mine structure or equipment'), ('$1,000', 'Provides restoration of original historical Lava Cap mine maps'),
              ('$5,000', 'Names a restored exhibit or structure in your honor')]
    tiers = [('Friend of the Mine', '$50/year', ['Free general admission for one', 'Quarterly updates', tc('1 yr free access to social media subscription')]),
             ('Gold Supporter', '$250/year', ['Free admission for two', 'Behind-the-scenes tour', 'Quarterly updates', tc('1 yr free access to social media subscription')]),
             ('Heritage Patron', '$1,000/year', ['Free admission for family', tc('Authentic payroll checkstub'), 'Private guided tour', 'All member benefits', 'Early access to special programs']),
             ('Legacy Partner', '$5,000+/year', ['Named exhibit sponsorship', 'Board recognition', 'All Patron benefits', 'Custom engagement opportunities', 'Annual impact report'])]
    imp = ''.join(f'<tr><td style="width:110px;color:var(--gold2);font-family:Georgia,serif;font-size:1.3rem">{a}</td><td>{d}</td></tr>' for a, d in impact)
    th = ''.join(f'<div class="card tier"><div class="pad"><h3>{n}</h3><div class="amt">{a}</div><ul>{"".join(f"<li>{x}</li>" for x in b)}</ul></div></div>' for n, a, b in tiers)
    P['donate.html'] = page('donate.html', 'Donate & Support | Lava Cap Historical Landmark',
        'Donate, become a member or volunteer to help preserve the Lava Cap Gold Mine in Nevada City, California. Lava Cap Historical Landmark is a 501(c)(3) non-profit.',
        f"""<section><div class="wrap split"><div><div class="eyebrow">Where Your Donation Goes</div><h2>Every contribution makes a difference</h2>
<p class="mute">Lava Cap Historical Landmark is a 501(c)(3) non-profit. Your gift supports preservation, education and community. {tc('EIN and tax-deductibility statement')}</p>
<a class="btn p" href="{PAYPAL}" target="_blank" rel="noopener">Make a Donation</a></div><table>{imp}</table></div></section>
<section class="alt"><div class="wrap"><div class="eyebrow">Membership</div><h2>Become a member</h2><div class="grid g4">{th}</div>
<p class="mute" style="margin-top:20px">Heritage Patron and Legacy Partner memberships are arranged by email: <a href="mailto:{EMAIL}?subject=Membership%20Inquiry">{EMAIL}</a></p></div></section>
<section><div class="wrap" style="max-width:820px"><div class="eyebrow">Give Your Time</div><h2>Volunteer with us</h2>
<p class="mute">Not in a position to give financially? Your time is just as valuable. We rely on volunteers for tours, events, preservation work and outreach.</p>
<ul class="mute"><li>Docent and tour guide</li><li>Event support</li><li>Preservation and grounds crew</li><li>Archive and research assistant</li><li>Outreach and social media</li></ul>
<a class="btn p" href="contact.html">Volunteer With Us</a></div></section>""",
        hero=('pages-home-preservation.jpg', 'Donate & Support', 'Invest in California\'s Heritage',
              'Your support makes it possible to restore, preserve and share the story of the Lava Cap Gold Mine with generations to come.', True))

    # ---------- BLOG ----------
    P['blog.html'] = page('blog.html', 'Stories from the Mine | Lava Cap Historical Landmark',
        'Stories, history and updates from the Lava Cap Historical Landmark in Nevada City, California.',
        f"""<section><div class="wrap" style="max-width:820px"><div class="eyebrow">Stories from the Mine</div><h2>History, nature and cleanup updates</h2>
<p class="mute">This section will hold the Landmark's stories: mine history, the people who worked here, the wildlife of the property and updates on the cleanup. Each post is checked against sources before it is published.</p>
<div class="notice">{tc('Misty to approve which of the existing posts move over. Posts that make claims about debt, liability or the cleanup need a source and review first.')}</div>
<p style="margin-top:20px"><a class="btn s" href="contact.html">Suggest a topic</a></p></div></section>""",
        hero=('pages-history-landscape.jpg', 'Stories', 'Stories from the Mine', 'Mine history, local wildlife and cleanup updates, written carefully and sourced.', True))

    # ---------- CONTACT ----------
    P['contact.html'] = page('contact.html', 'Contact | Lava Cap Historical Landmark',
        'Contact the Lava Cap Historical Landmark in Nevada City, CA to plan a visit, book a program, donate or volunteer.',
        f"""<section><div class="wrap grid g2"><div><div class="eyebrow">Get in Touch</div><h2>We would love to hear from you</h2>
<p class="mute">Planning a visit, booking a school program, or want to get involved? Reach out and we will get back to you promptly.</p>
<table><tr><th>Email</th><td><a href="mailto:{EMAIL}">{EMAIL}</a></td></tr><tr><th>Phone</th><td>{tc('Phone or voicemail number')}</td></tr>
<tr><th>Location</th><td>Nevada City, CA 95959<br>{tc('Mailing address')}</td></tr><tr><th>Hours</th><td>{tc('Office or visitor hours')}</td></tr></table></div>
<form action="contact.php" method="post"><label for="n">Your name</label><input id="n" name="name" required>
<label for="e">Email</label><input id="e" name="email" type="email" required>
<label for="r">I am contacting you about</label><select id="r" name="reason"><option>Plan a visit</option><option>Book a school or group program</option><option>Donations and membership</option><option>Volunteering</option><option>Research partnerships</option><option>Something else</option></select>
<label for="m">Message</label><textarea id="m" name="message" required></textarea>
<input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true"><p style="margin-top:16px"><button class="btn p" type="submit" style="cursor:pointer">Send message</button></p></form></div></section>""",
        hero=('pages-history-equipment.jpg', 'Contact', 'Let\'s Talk', 'Questions about hours, programs, donations or volunteering are all welcome.', True))

    P['thanks.html'] = page('thanks.html', 'Thank you | Lava Cap Historical Landmark', 'Thank you for contacting Lava Cap Historical Landmark.',
        '<section><div class="wrap" style="max-width:700px;text-align:center"><h2>Thank you</h2><p class="mute">Your message was sent. We will be in touch soon.</p><a class="btn p" href="index.html">Back to home</a></div></section>')
    P['404.html'] = page('404.html', 'Page not found | Lava Cap Historical Landmark', 'Page not found.',
        '<section><div class="wrap" style="max-width:700px;text-align:center"><h2>Page not found</h2><p class="mute">That page does not exist or has moved.</p><a class="btn p" href="index.html">Back to home</a></div></section>')
    P['privacy.html'] = page('privacy.html', 'Privacy Policy | Lava Cap Historical Landmark', 'Privacy policy for lavacapmine.com.',
        f'<section><div class="wrap" style="max-width:760px"><h2>Privacy Policy</h2><p class="mute">This site does not use advertising trackers. When you use the contact form we collect the name, email and message you send so we can reply. We do not sell or share this information. Donations are processed by PayPal under its own privacy policy. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p><p>{tc("Replace with the privacy policy text from the current site if it must be kept")}</p></div></section>')
    P['terms.html'] = page('terms.html', 'Terms of Use | Lava Cap Historical Landmark', 'Terms of use for lavacapmine.com.',
        f'<section><div class="wrap" style="max-width:760px"><h2>Terms of Use</h2><p class="mute">Content on this site is provided for general information about the Lava Cap Historical Landmark. Historical details are compiled from available sources and may be updated. Photographs and text may not be reused without permission. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p><p>{tc("Replace with the terms text from the current site if it must be kept")}</p></div></section>')
    return P


CONTACT_PHP = """<?php
// Simple contact handler for Hostinger shared hosting. Set $to, then test once after upload.
$to = 'admin@lavacapmine.com';
if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !empty($_POST['website'])) { header('Location: index.html'); exit; }
$name = trim(strip_tags($_POST['name'] ?? ''));
$email = filter_var($_POST['email'] ?? '', FILTER_VALIDATE_EMAIL);
$reason = trim(strip_tags($_POST['reason'] ?? ''));
$msg = trim(strip_tags($_POST['message'] ?? ''));
if (!$name || !$email || !$msg) { http_response_code(400); echo 'Please go back and fill in every field.'; exit; }
$subject = 'Website message: ' . preg_replace('/[\\r\\n]+/', ' ', $reason);
$body = "Name: $name\\nEmail: $email\\nTopic: $reason\\n\\n$msg\\n";
$headers = "From: no-reply@lavacapmine.com\\r\\nReply-To: $email\\r\\n";
@mail($to, $subject, $body, $headers);
header('Location: thanks.html');
"""

HTACCESS = """ErrorDocument 404 /404.html
Options -Indexes
<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css application/javascript application/ld+json image/svg+xml
</IfModule>
<IfModule mod_expires.c>
ExpiresActive On
ExpiresByType image/jpeg "access plus 1 year"
ExpiresByType image/png "access plus 1 year"
ExpiresByType text/css "access plus 1 month"
</IfModule>
"""

if __name__ == '__main__':
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)
    shutil.copytree(os.path.join(SRC, 'images'), os.path.join(DIST, 'images'))
    open(os.path.join(DIST, 'style.css'), 'w').write(CSS)
    P = pages()
    for f, h in P.items():
        open(os.path.join(DIST, f), 'w').write(h)
    open(os.path.join(DIST, 'contact.php'), 'w').write(CONTACT_PHP)
    open(os.path.join(DIST, '.htaccess'), 'w').write(HTACCESS)
    open(os.path.join(DIST, 'robots.txt'), 'w').write(
        f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n' if LIVE else 'User-agent: *\nDisallow: /\n')
    urls = [f for f in P if f not in ('404.html', 'thanks.html')]
    open(os.path.join(DIST, 'sitemap.xml'), 'w').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join(f'<url><loc>{SITE}/{"" if u=="index.html" else u}</loc></url>\n' for u in urls) + '</urlset>\n')
    zp = os.path.join(ROOT, 'lava-cap-site-' + ('live' if LIVE else 'preview') + '.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in os.walk(DIST):
            for f in fs:
                p = os.path.join(d, f)
                z.write(p, os.path.relpath(p, DIST))
    print('built', len(P), 'pages ->', zp, os.path.getsize(zp) // 1024, 'KB')
