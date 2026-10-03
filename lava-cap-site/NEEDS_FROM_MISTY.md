# Lava Cap Historical Landmark: what we still need from Misty

The temporary preview marks each of these with a gold "TO CONFIRM" tag.

## Contact and location
1. A phone or voicemail number (none is published anywhere today).
2. A mailing address, and a street address or meeting point for GPS and directions.
3. Office or visitor hours to show on the Contact page.
4. Parking details for the Visit page.

## Opening and visiting (the old site said hours Thu-Sun, but she says no visitors until about spring 2027)
5. Confirm "opening spring 2027" and when she wants hours and admission published.
6. Planned hours and admission prices when they are known.
7. Docent tour days and times (the old site said Sat/Sun 10:30 and 2:00).
8. Confirm the welcome center and wheelchair access exist or are planned. The photo on the home page is a concept image.

## Site safety and the EPA cleanup
9. Current EPA status, which areas are open to the public, and any access rules.
10. Who reviewed the wording (a lawyer or the nonprofit's board).
11. The old blog says the nonprofit owes the government $33 million. Where does that figure come from? It stays off the site until it has a source.

## Facts and quotes from the old site
12. The old site credited a quote to a "California Gold Rush Proverb" and one to the "Nevada County Historical Society". We left both out. Send sources if she wants them back.
13. The old site said "300 ounces of gold per ton of ore" (and the new blog says 300 ounces of silver per ton). Both look wrong. We left the figure out of the history page.
14. Source for "number one silver-producing hard-rock mine in America" (kept, tagged).

## Programs and giving
15. Which workshops (beekeeping, wood skills, field trips) are real for 2027, and any free offer for Title I schools.
16. Membership perks: "1 yr free access to social media subscription" and "authentic payroll checkstub" (both tagged).
17. EIN and the tax-deductibility sentence for the Donate page.
18. Confirm the PayPal donate button is the right account.

## Blog
19. Which of the 28 existing posts move over. Posts about debt, liability and the cleanup need a source and a review first.

## Photos and legal
20. OK to reuse the photos from the current site (all 13 are on the preview).
21. Privacy policy and terms text from the current site, if she wants them kept as written.

## Account and cutover (for Novah)
22. DNS: change only the website records at GoDaddy. Leave nameservers and the MX records for Microsoft 365 email alone.
23. Keep the GoDaddy Airo plan until the new site is live. It renews Oct 9 at $49.99, so decide whether one more month is fine.
24. At launch, run `python3 build.py --live` (removes noindex, opens robots.txt, adds the sitemap).
25. Test the contact form once on Hostinger (`contact.php` uses PHP mail()).
