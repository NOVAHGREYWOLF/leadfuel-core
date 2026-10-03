from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether
NAVY=colors.HexColor('#0d141a');RED=colors.HexColor('#e00000');GREY=colors.HexColor('#f1f1f1');LINE=colors.HexColor('#e1e3e6');TXT=colors.HexColor('#1d1e20')
W,H=letter
def page(c,d):
    c.saveState()
    hh=0.55*inch if d.page>1 else 1.6*inch
    c.setFillColor(NAVY);c.rect(0,H-hh,W,hh,fill=1,stroke=0)
    c.setFillColor(colors.HexColor('#fc0000'));c.rect(0,H-hh-4,W,4,fill=1,stroke=0)
    c.setFillColor(colors.white);c.setFont('Helvetica-Bold',22);c.drawString(42,H-36,'etg.ai')
    c.setFillColor(colors.HexColor('#b9bcc2'));c.setFont('Helvetica',8);c.drawRightString(W-42,H-34,'A S S E S S .   A D A P T .   A D V A N C E .')
    if d.page==1:
        c.setFillColor(colors.HexColor('#ff6b6b'));c.setFont('Helvetica',9);c.drawString(42,H-60,'W E B S I T E   A U D I T')
        c.setFillColor(colors.white);c.setFont('Helvetica-Bold',22);c.drawString(42,H-84,'Lava Cap Historical Landmark')
        c.setFillColor(colors.HexColor('#b9bcc2'));c.setFont('Helvetica',9.5);c.drawString(42,H-101,'lavacapmine.com  |  Prepared for Misty Elder  |  September 29, 2026')
    c.setFillColor(NAVY);c.rect(0,0,W,0.35*inch,fill=1,stroke=0)
    c.setFillColor(colors.HexColor('#b9bcc2'));c.setFont('Helvetica',8)
    c.drawString(42,14,'Audit done by Novah Greywolf  |  novahgreywolf@etg.ai  |  etg.ai')
    c.drawRightString(W-42,14,'Page %d  |  Confidential, prepared for Lava Cap Historical Landmark'%d.page)
    c.restoreState()
doc=BaseDocTemplate('Lava_Cap_Audit_ETG.pdf',pagesize=letter,title='Lava Cap Historical Landmark - Website Audit',author='Novah Greywolf, etg.ai')
def fr(top):return Frame(42,0.5*inch,W-84,H-top-0.55*inch,id='f',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
doc.addPageTemplates([PageTemplate(id='first',frames=[fr(1.6*inch+18)],onPage=page,autoNextPageTemplate='rest'),PageTemplate(id='rest',frames=[fr(0.55*inch+18)],onPage=page)])
b=ParagraphStyle('b',fontName='Helvetica',fontSize=9.6,leading=13.4,textColor=TXT,spaceAfter=6)
h2=ParagraphStyle('h2',parent=b,fontName='Helvetica-Bold',fontSize=13.5,leading=17,spaceBefore=10,spaceAfter=5,textColor=NAVY,borderPadding=(0,0,0,7))
h3=ParagraphStyle('h3',parent=b,fontName='Helvetica-Bold',fontSize=10.5,spaceBefore=6,spaceAfter=2)
li=ParagraphStyle('li',parent=b,leftIndent=12,bulletIndent=2,spaceAfter=3)
sm=ParagraphStyle('sm',parent=b,fontSize=8.8,leading=11.5,spaceAfter=0)
th=ParagraphStyle('th',parent=sm,fontName='Helvetica-Bold',textColor=colors.white)
def P(t,s=b):return Paragraph(t,s)
def tag(t):
    c={'HIGH':'#e00000','MED':'#c77700','FIX':'#c77700','WATCH':'#56585e','LOW':'#56585e','PASS':'#00785a'}[t]
    return Paragraph('<font color="%s"><b>%s</b></font>'%(c,t),sm)
def tbl(rows,widths,head=True):
    t=Table(rows,colWidths=widths,repeatRows=1 if head else 0)
    st=[('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),0.5,LINE),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),6)]
    if head: st.append(('BACKGROUND',(0,0),(-1,0),NAVY))
    t.setStyle(TableStyle(st));return t
def H2(t):return Table([[P(t,h2)]],colWidths=[W-84],style=[('LINEBEFORE',(0,0),(0,0),3.5,RED),('LEFTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)])
S=[]
S+=[H2('Summary'),P('Lava Cap Historical Landmark is a six page site (Home, History, Education, Visit, Donate, Contact) for a 501(c)(3) working to turn the Lava Cap Gold Mine into an educational site. It is built on the GoDaddy Airo builder. The design and structure are solid. What holds it back is missing contact details, information that contradicts itself, and a few claims that need checking before more people find the site.')]
stat=[[P('<font size=17><b>6</b></font><br/>pages reviewed',sm),P('<font size=17 color="#e00000"><b>0</b></font><br/>phone numbers',sm),P('<font size=17 color="#e00000"><b>2</b></font><br/>conflicting hours',sm),P('<font size=17 color="#00785a"><b>6/6</b></font><br/>pages have titles and descriptions',sm)]]
t=Table(stat,colWidths=[(W-84)/4]*4);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GREY),('LINEAFTER',(0,0),(2,0),4,colors.white),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('ALIGN',(0,0),(-1,-1),'CENTER')]))
for p in t._cellvalues[0]:p.style=ParagraphStyle('c',parent=sm,alignment=1)
S+=[t,Spacer(1,6),H2('What is working')]
for x in ['<b>Clear mission and story.</b> Visitors understand what the place is within seconds, and the History page has a real timeline.','<b>Good search basics.</b> Each page has its own title and description, a canonical address, a sitemap listing all six pages, and a robots file that allows Google in. Images have descriptive alt text and each page has one main heading.','<b>Ways to give.</b> A PayPal donate button, donation levels, a volunteer path and a newsletter sign up are all present.','<b>Compliance basics.</b> Privacy policy, terms of use and a cookie consent banner are in place. The Visit page covers accessibility and parking.','<b>Social profiles linked.</b> Facebook, Instagram, YouTube, X and Twitch, all on the lavacapmine handles.']:S.append(Paragraph(x,li,bulletText='•'))
S+=[H2('Priority fixes at a glance')]
rows=[[P('#',th),P('Fix',th),P('Priority',th),P('Effort',th)]]
for i,(f,p,e) in enumerate([('Add a phone number, mailing or street address and a visible contact block in the footer','HIGH','15 min'),('Make hours, tour schedule and admission match on every page','HIGH','30 min'),('Verify or remove the unsourced quotes and the gold-per-ton figure','HIGH','30 min'),('Add a plain-language site safety and EPA cleanup status section','HIGH','1 to 2 hrs'),('Replace placeholder text on the Donate page','MED','20 min'),('Return a real “not found” response for bad addresses','MED','Builder setting'),('Add structured data, photos of the real site and a Google Business Profile','MED','1 to 2 hrs'),('Fix the “Lave Cap” typo and trim page weight','LOW','15 min')],1):rows.append([P(str(i),sm),P(f,sm),tag(p),P(e,sm)])
S.append(tbl(rows,[28,(W-84)-28-60-80,60,80]))
S+=[H2('1. Trust and contact'),P('No phone number, no street address  '+'<font color="#e00000"><b>HIGH</b></font>',h3),P('The only contact route is admin@lavacapmine.com and a generic “Nevada City, CA 95959.” The Visit page tells people to “call ahead,” but no number exists. Directions read “approximately 60 miles northeast of Sacramento,” with no address to type into a map. Visitors, teachers booking field trips and donors all need a person to reach. <b>Fix:</b> add a phone or voicemail line, a mapped address or meeting point, and put both in the footer of every page.'),
P('The calendar does not exist  <font color="#e00000"><b>HIGH</b></font>',h3),P('Hours “may vary on holidays and during special events. Please check our calendar.” There is no calendar page or link. The addresses /calendar and /events show the same generic page. <b>Fix:</b> add a simple events list or remove the sentence.'),
P('Placeholder wording is still live  <font color="#c77700"><b>MED</b></font>',h3)]
for x in ['Admission: “Pricing to be announced. Please check back closer to our opening.” This conflicts with “open to visitors” on the same page.','Guided tour price: “Included with subscription.” There is no subscription anywhere on the site.','Donation levels list “1 yr Free access to social media subscription” twice and “Authentic Payroll checkstub.” These read as drafts.']:S.append(Paragraph(x,li,bulletText='•'))
S+=[H2('2. Accuracy and consistency')]
rows=[[P('Item',th),P('What the site says',th),P('Action',th)]]
for a,b_,c in [('Hours','Visit page: Thu–Fri 10–4, Sat–Sun 9–5, closed Mon–Wed. Contact page: Thu–Sun 9–5.','Pick the real hours and show them once, reused everywhere.'),('Tours','History page: “guided tours available year-round.” Visit page: guided tours on weekends and by appointment for groups of 10 or more.','Confirm current tour schedule and wording.'),('Quotes','“California Gold Rush Proverb” and a quote credited to the “Nevada County Historical Society.”','Add a real source or remove. Unsourced quotes hurt a history site.'),('Gold recovery','“300 ounces of gold per ton of ore processed.”','Looks like a typo. Public sources describe the mine’s total output in ounces; check the figure.'),('Facilities','“Welcome center,” “research facilities,” bus and shuttle options, “free on-site parking.”','Confirm each exists today. If planned, label it “coming soon.”'),('Workshops','Beekeeping and chainsaw/wood milling programs sit beside history programs.','Confirm they are active and add dates or a booking route.')]:rows.append([P('<b>%s</b>'%a,sm),P(b_,sm),P(c,sm)])
S.append(tbl(rows,[90,(W-84)-90-170,170]))
S+=[H2('3. Site safety and EPA cleanup status  <font color="#e00000" size=9>HIGH</font>'),P('Public records list the Lava Cap Mine as an EPA Superfund cleanup site for arsenic, placed on the National Priorities List in 1999 (see USGS and EPA pages on the Lava Cap Mine Superfund Site). The website invites visitors, school groups and children, and does not mention this anywhere. Search results for “Lava Cap Mine” will surface the EPA material either way. A short, plain-language section on current access rules, what areas are open and what the cleanup status is would build trust with parents, teachers and donors, and reduce the chance of surprises. We recommend the wording be reviewed by whoever advises the nonprofit on access and liability.'),
Table([[P('<b>Note:</b> we have not verified current EPA status or site access rules. This is a flag for you to confirm, not a conclusion.',sm)]],colWidths=[W-84],style=[('BACKGROUND',(0,0),(-1,-1),GREY),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]),
H2('4. Technical and search')]
rows=[[P('Check',th),P('Result',th),P('Detail',th)]]
for a,r,d in [('Page titles and descriptions','PASS','Unique on all six pages, with sensible length.'),('Sitemap and robots','PASS','Sitemap lists all six pages and robots.txt allows crawling.'),('Canonical and social sharing tags','PASS','Canonical address and Open Graph tags are set. One shared og-image is used for every page.'),('Image alt text and headings','PASS','Descriptive alt text; one H1 per page.'),('Bad addresses','FIX','Made-up addresses such as /nonexistent-xyz load with a normal “200 OK” status instead of “404 not found.” Google may index empty pages.'),('Structured data','FIX','None found. Adding nonprofit and place markup helps Google show hours, address and donate details.'),('Page weight','WATCH','One 600 KB script loads on every page. Fine on wifi, slower on rural mobile service near Nevada City.'),('Typos','FIX','“Lave Cap Gold Mine District” appears on the History page.'),('Cookie banner and analytics','PASS','Consent banner present. We could not confirm which analytics tool is connected.')]:rows.append([P(a,sm),tag(r),P(d,sm)])
S.append(tbl(rows,[150,55,(W-84)-205]))
S+=[H2('5. Google presence'),P('This pass did not include Google Business Profile or map results. Searches for the Landmark returned mainly EPA, USGS and Wikipedia pages about the mine, which is a reason to claim and complete a Google Business Profile: hours, photos, link to the donate page and the safety information above. Recommended next step: confirm whether a profile exists and who owns it.'),
H2('6. Website cost check'),P('From the GoDaddy receipts: the Airo website plan is $49.99 per month ($599.88 a year), up from $21.99 per month in 2025, on top of email, domain and protection. The site is six mostly static pages with a PayPal button. Before the October 9 renewal, it is worth pricing a lower cost plan or a simple hosted build, and confirming the payment method that GoDaddy flagged.'),
H2('7. Suggested plan')]
rows=[[P('When',th),P('What',th)]]
for a,d in [('This week','Confirm hours, tours, admission and facilities. Add phone, address and footer contact. Replace placeholder text and the typo. Fix or remove the unsourced quotes.'),('Next 2 weeks','Add the site safety section, an events list, structured data and real photos. Claim the Google Business Profile.'),('Before Oct 9','Decide whether to keep the current plan. Update the payment method on the account.')]:rows.append([P('<b>%s</b>'%a,sm),P(d,sm)])
S+=[tbl(rows,[80,(W-84)-80]),Spacer(1,6),Table([[P('<b>Privacy note:</b> a login email in the inbox contains an account password in plain text. Please change that password and use a password manager or shared vault to send credentials in the future.',sm)]],colWidths=[W-84],style=[('BACKGROUND',(0,0),(-1,-1),GREY),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])]
doc.build(S)
