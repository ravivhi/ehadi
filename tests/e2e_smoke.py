"""End-to-end test for Mathoria (Playwright, headless Edge).

Run:  python tests/e2e_smoke.py [--shots DIR] [--headed]

Opens index.html from disk with an empty browser profile and fails on any page error, console error or
recorded app error. Covers the picture-first game for children who can't read yet: the 3-step first run
(a grown-up enters name and grade, the child picks boy or girl and a look), the home screen with the child's
drawn character (one big play button, the worlds and the prize shop; no menus, missions, streaks, XP or daily
goal), every screen saying its instruction out loud, Hebrew text and speech in the child's gender, locked
things explaining themselves, the world path and its games, Math Detective in the Puzzle Cave, every flagship
game, leaving with X and resuming from the play button, the prize shop (gender-matched prizes drawn on the
child, try-on, buy with X / check, dresses replace pants, too few coins), "my look", the grown-ups lock in
front of the weekly report (numbers, days, topics with an example question, next week) and the settings,
several players on one device, old saves (old avatars and items) and old links,
grade 6 content, and phone/tablet layouts.
"""
import argparse
import os
import pathlib
import re
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = ROOT.joinpath('index.html').as_uri()

# A recording speech engine, so read-aloud can be checked without audio.
FAKE_SPEECH = """(() => {
  const spoken = []; window.__spoken = spoken; window.__cancels = 0;
  const voices = [{ name: 'Fake English', lang: 'en-US', localService: true }, { name: 'Fake Hebrew', lang: 'he-IL', localService: true }];
  const fake = { speaking: false, getVoices: () => voices, addEventListener() {}, removeEventListener() {},
    cancel() { window.__cancels++; }, resume() {}, pause() {},
    speak(u) { spoken.push({ text: u.text, lang: u.lang, voice: u.voice && u.voice.name }); setTimeout(() => u.onend && u.onend({ type: 'end' }), 5); } };
  Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true, writable: true });
  Object.defineProperty(window, 'SpeechSynthesisUtterance', { value: function (text) { this.text = text; }, configurable: true, writable: true });
})();"""

ME = "MA.db.get('students', MA.svc.student().id)"


class Run:
    def __init__(self, page, shots):
        self.page, self.shots, self.errors, self.n, self.ok = page, shots, [], 0, True
        page.on('pageerror', lambda e: self.errors.append('pageerror: ' + str(e)))
        page.on('console', lambda m: self.errors.append('console: ' + m.text) if m.type == 'error' else None)

    def go(self, hash_, wait=300):
        self.page.evaluate('h => MA.router.go(h)', hash_)
        self.page.wait_for_timeout(wait)

    def wait_hash(self, prefix, timeout=20000):
        self.page.wait_for_function('p => location.hash.startsWith(p)', arg=prefix, timeout=timeout)
        self.page.wait_for_timeout(200)

    def hash(self):
        return self.page.evaluate('() => location.hash')

    def shot(self, name):
        self.n += 1
        self.page.screenshot(path=os.path.join(self.shots, f'{self.n:02d}_{name}.png'), full_page=True)

    def check(self, label):
        if self.errors:
            print(f'[{label}] ERRORS:')
            for e in self.errors:
                print('   ', e[:400])
            self.errors.clear()
            self.ok = False

    def expect(self, cond, label):
        if not cond:
            print(f'[{label}] EXPECTATION FAILED')
            self.ok = False

    def modal(self):
        return self.page.locator('#modal-root .modal-back').last

    def modal_primary(self, wait=300):
        m = self.modal()
        m.wait_for(timeout=15000)
        m.locator('.modal-foot .btn-primary, .modal-foot .btn-danger').last.click()
        self.page.wait_for_timeout(wait)

    def modals(self):
        return self.page.locator('#modal-root .modal-back').count()

    def open_gate(self):
        self.page.locator('.s-top > button').last.click()
        m = self.modal()
        m.locator('.gate-q').wait_for(timeout=10000)
        return m

    def open_settings(self, tab='settings'):
        """Through the grown-ups lock: read the multiplication and type the answer. Opens on the weekly report."""
        m = self.open_gate()
        a, b = map(int, re.findall(r'\d+', m.locator('.gate-q').inner_text())[:2])
        m.locator('.gate-in').fill(str(a * b))
        m.locator('.modal-foot .btn-primary').click()
        self.page.wait_for_selector('#modal-root .modal-back .grown-tabs', timeout=10000)
        if tab == 'settings':
            self.modal().locator('.grown-tabs button[data-tab="settings"]').click()
            self.page.wait_for_selector('#modal-root .modal-back .field select', timeout=10000)
        else:
            self.page.wait_for_selector('#modal-root .modal-back .rp', timeout=10000)
        self.page.wait_for_timeout(450)

    def set_me(self, js):
        self.page.evaluate('() => { const s = ' + ME + '; ' + js + '; MA.db.saveNow(); }')

    def player(self):
        return self.page.evaluate('() => { const s = MA.svc.student(); return { name: s.name, grade: s.grade, lang: s.lang, onboarded: s.onboarded, gender: s.gender }; }')

    def shop_genders(self):
        return self.page.evaluate("() => [...document.querySelectorAll('.shop-item')].map(b => MA.db.get('shopItems', b.dataset.id).gender)")

    def spoken(self):
        return self.page.evaluate('() => window.__spoken.map(s => s.text).join(" | ")')

    def hush(self):
        self.page.evaluate('() => { window.__spoken.length = 0; }')

    def start(self):
        """Open a game's first question (press the intro card's play button if there is one)."""
        p = self.page
        p.wait_for_selector('.player')
        for _ in range(30):
            if p.locator('.pl-card .answer-area').count():
                return
            if p.locator('.pl-card .btn-go').count():
                p.locator('.pl-card .btn-go').first.click()
            p.wait_for_timeout(150)

    def onboard(self, name, grade, gender='f', shots=False):
        p = self.page
        p.wait_for_selector('.onb input.input')
        p.fill('.onb input.input', name)
        p.locator('.onb .pick-grid .pick').nth(grade - 1).click()
        p.click('.onb-nav .btn-go')                          # on to boy or girl
        p.wait_for_selector('.onb .gender-pick')
        if shots:
            self.shot('onboarding_gender')
        p.locator('.onb .gender-pick').nth(0 if gender == 'm' else 1).click()
        p.wait_for_selector('.onb .look-pickers')
        p.locator('.onb .lp-row').nth(0).locator('.lp-dot').nth(3).click()       # skin
        p.locator('.onb .lp-hair').nth(2).click()                                # hair style
        p.locator('.onb .lp-row').nth(4).locator('.lp-dot').nth(1).click()       # shirt
        if shots:
            self.shot('onboarding_look')
        p.click('.onb-nav .btn-go')                          # the rocket
        self.wait_hash('#/s/play/')
        self.expect(self.play(), 'onboarding activity finishes')
        self.go('#/s/home')
        p.wait_for_selector('.play-big')

    def play(self, max_q=40, wrong_first=False):
        """Answer questions through the player hook until the finish screen appears."""
        p = self.page
        for i in range(max_q):
            p.wait_for_timeout(120)
            if p.locator('.finish').count():
                return True
            if not p.evaluate('() => !!(MA.player._current && document.querySelector(".pl-card .answer-area"))'):
                intro = p.locator('.pl-card .btn-go')
                if intro.count():
                    intro.first.click()
                    continue
                p.wait_for_timeout(300)
                continue
            if wrong_first and i % 3 == 0:
                p.evaluate('() => MA.player._current.answer("__wrong__")')
                p.wait_for_timeout(80)
            p.evaluate('() => MA.player._current.answer(MA.player._current.q.answer)')
            p.wait_for_timeout(120)
            nxt = p.locator('.pl-bottom .btn-next')
            if nxt.count():
                nxt.first.click()
        return p.locator('.finish').count() > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default=os.path.join(tempfile.gettempdir(), 'math_app_shots'))
    ap.add_argument('--headed', action='store_true')
    args = ap.parse_args()
    os.makedirs(args.shots, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='msedge', headless=not args.headed)
        ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='en-US')
        ctx.add_init_script(FAKE_SPEECH)
        page = ctx.new_page()
        r = Run(page, args.shots)
        try:
            run_flows(r, page)
        except Exception as e:  # report instead of a bare traceback, keep screenshots
            print(f'EXCEPTION: {type(e).__name__}: {str(e)[:800]}')
            r.shot('exception')
            r.ok = False
        browser.close()
    print('SHOTS:', args.shots)
    print('RESULT:', 'PASS' if r.ok else 'FAIL')
    sys.exit(0 if r.ok else 1)


def run_flows(r, page):
    # ---- first run: straight into a 2-step setup, no accounts, no demo, no top bar
    page.goto(URL)
    r.wait_hash('#/s/onboarding')
    text = page.locator('body').inner_text()
    r.expect(not any(w in text for w in ['Log in', 'Sign up', 'Demo', '\u05d4\u05d3\u05d2\u05de\u05d4', 'password']), 'no account or demo UI')
    r.expect(page.locator('.onb .pick-grid .pick').count() == 6, 'grades 1 to 6 offered')
    r.expect(page.locator('.s-top').count() == 0, 'no top bar during setup')
    r.shot('first_launch')
    page.locator('.onb .seg button').first.click()          # Hebrew
    page.wait_for_timeout(300)
    r.expect(page.evaluate('document.documentElement.dir') == 'rtl', 'Hebrew switches to RTL')
    r.expect('\u05de\u05ea\u05de\u05d8\u05d5\u05e8\u05d9\u05d4' in page.locator('.onb h1').inner_text(), 'Hebrew welcome')
    r.shot('first_launch_he')
    page.locator('.onb .seg button').last.click()           # back to English
    page.wait_for_timeout(300)
    r.expect(page.evaluate('document.documentElement.dir') == 'ltr', 'English is LTR')
    r.hush()
    r.onboard('Noa', 2, gender='f', shots=True)
    r.expect(r.player() == {'name': 'Noa', 'grade': 2, 'lang': 'en', 'onboarded': True, 'gender': 'f'}, 'onboarding saved name, grade, language and girl')
    look = page.evaluate('() => { const a = MA.svc.student().avatar, AV = MA.avatar; return [a.v, a.skin === AV.SKINS[3], a.hair === AV.BASE_HAIR.f[2], a.top === AV.TEES[1]]; }')
    r.expect(look == [2, True, True, True], 'the chosen look was saved: ' + str(look))
    r.expect(page.evaluate('() => MA.svc.student().settings.readAloud === true'), 'read-aloud is on for new players')
    said = r.spoken()
    r.expect('Are you a boy or a girl' in said and 'Now choose how you look' in said, 'the boy/girl and look steps say what to do')
    r.expect('Press the big button' in said, 'home says what to do')

    # ---- home: the child's own character, one big play button, the worlds and the prize shop
    r.expect('Noa' in page.locator('.hh-bubble').inner_text(), 'home greets the player')
    r.expect(page.locator('.hh-buddy .figure svg').count() == 1 and page.locator('.s-me .av-pic svg').count() == 1, 'the drawn character on the home screen and in the top bar')
    r.expect(page.locator('.world-card').count() >= 4 and page.locator('.shop-card').count() == 1, 'worlds and the prize shop on the home screen')
    r.expect(page.locator('.world-card.locked').count() == 1, 'only the Puzzle Cave starts locked')
    text = page.locator('body').inner_text()
    r.expect(not any(w in text for w in ['Daily goal', 'Mission', 'Streak', 'XP', 'Badges', 'Level']), 'no daily goal, missions, streaks, XP, badges or levels')
    r.expect(page.locator('.s-nav, .bell, .top-home').count() == 0, 'no menu bar, notifications or home button on the home screen')
    print('   home text:', ' / '.join(x.strip() for x in text.split('\n') if x.strip()))
    r.shot('home')
    r.hush()
    page.locator('.world-card.locked').first.click()
    page.wait_for_timeout(300)
    r.expect('still locked' in r.spoken() and r.hash() == '#/s/home', 'a locked world says why and stays put')
    r.check('first run + home')

    # ---- progress survives a reload; old saves move to the simple game; old links open the game
    xp = page.evaluate('() => MA.svc.student().totalXp')
    coins = page.evaluate('() => MA.svc.student().coins')
    r.set_me("s.ui = 1; s.settings.readAloud = false; s.settings.timed = true; s.goals = { dailyMinutes: 15 }; s.streak = { days: 3 }; "
             "s.avatar = { base: '\U0001F98A', color: '#FFD6A5' }; delete s.gender; s.inventory = ['acc_cap', 'char_robot', 'pet_turtle']; s.equipped = { acc: 'acc_cap', pet: 'pet_turtle' }")
    page.reload()
    r.wait_hash('#/s/me')
    r.expect(page.locator('.gender-pick').count() == 2, 'an old player is asked once: boy or girl?')
    r.shot('old_player_gender')
    page.locator('.gender-pick').nth(1).click()
    page.wait_for_selector('.look-pickers')
    r.go('#/s/home')
    page.wait_for_selector('.play-big')
    r.expect(r.hash() == '#/s/home', 'then the game home')
    r.expect(page.evaluate('() => MA.svc.student().totalXp') == xp and xp > 0, 'progress kept after reload')
    mig = page.evaluate("() => { const s = MA.svc.student(); return [s.ui, s.settings.readAloud, 'timed' in s.settings, 'goals' in s, 'streak' in s, s.gender, s.avatar.v, s.inventory.slice().sort().join(','), s.equipped.hat, s.equipped.pet, s.coins]; }")
    r.expect(mig == [3, True, False, False, False, 'f', 2, 'hat_cap_red,pet_turtle', 'hat_cap_red', 'pet_turtle', coins + 100],
             'old saves: read-aloud on, removed features gone, new character, old items swapped or refunded: ' + str(mig))
    for old in ['#/login', '#/demo', '#/p/overview', '#/a/dashboard', '#/register?role=parent', '#/',
                '#/s/world', '#/s/practice', '#/s/challenges', '#/s/progress', '#/s/daily', '#/s/skill/g2-add-mental']:
        r.go(old)
        r.expect(r.hash() == '#/s/home', 'old link opens the game home: ' + old)
    r.check('reload + old saves + old links')

    # ---- the big play button: picture buttons, the question read aloud, a picture finish screen
    r.hush()
    page.locator('.play-big').click()
    page.wait_for_selector('.player')
    r.expect(page.locator('.s-top').count() == 0, 'no top bar while playing')
    page.wait_for_timeout(300)
    if page.locator('.pl-card .btn-go').count():
        r.shot('player_intro')
    r.start()
    page.wait_for_timeout(600)
    r.expect(len(r.spoken()) > 0, 'the question is read aloud by itself')
    r.expect(page.locator('.pl-bottom .btn-check').inner_text().strip() == '\u2714', 'the check button is a picture')
    r.shot('player_question')
    page.evaluate('() => MA.player._current.answer("__wrong__")')
    page.wait_for_timeout(300)
    r.shot('player_try_again')
    r.expect(r.play(wrong_first=True), 'the play button game finishes')
    fin = page.locator('.finish').inner_text()
    r.expect(page.locator('.finish-btns .btn-round').count() >= 2 and 'XP' not in fin, 'picture finish screen without XP')
    r.shot('player_finish')
    r.check('play button')

    # ---- X leaves at once (no question to read); the play button picks the game up again
    r.go('#/s/home')
    page.locator('.play-big').click()
    r.start()
    page.evaluate('() => MA.player._current.answer(MA.player._current.q.answer)')
    page.wait_for_timeout(200)
    page.locator('.pl-bottom .btn-next').click()
    page.wait_for_timeout(300)
    page.locator('.pl-exit').click()
    r.wait_hash('#/s/home')
    page.wait_for_timeout(300)
    r.expect(r.modals() == 0, 'no "are you sure" when leaving')
    href = page.locator('.play-big').get_attribute('href') or ''
    r.expect('resume=1' in href, 'the play button resumes the unfinished game: ' + href)
    page.locator('.play-big').click()
    page.wait_for_selector('.player')
    r.expect(r.play(), 'the resumed game finishes')
    r.check('exit + resume')

    # ---- a world: the path with one arrow, locked circles, and the world's games
    r.go('#/s/home')
    r.hush()
    page.locator('a.world-card').first.click()
    r.wait_hash('#/s/world/')
    page.wait_for_selector('.trail .node')
    r.expect(page.locator('.n-flag').count() == 1, 'one arrow shows where to play next')
    r.expect('Press a circle' in r.spoken(), 'the world says what to do')
    r.expect(page.locator('.top-home').count() == 1, 'a home button outside the home screen')
    r.shot('world')
    locked = page.locator('button.node.locked')
    if locked.count():
        r.hush()
        locked.first.click()
        page.wait_for_timeout(300)
        r.expect('still locked' in r.spoken() and r.hash().startswith('#/s/world/'), 'a locked circle says why')
    page.locator('a.node.current').first.click()
    r.wait_hash('#/s/play/')
    r.expect(r.play(), 'the next circle on the path finishes')
    tiles = 0
    for wid in page.evaluate('() => MA.content.worlds().filter(w => MA.game.worldUnlocked(MA.svc.student(), w)).map(w => w.id)'):
        r.go('#/s/world/' + wid, wait=400)
        tiles += page.locator('.game-tile').count()
        if wid == 'village':
            r.shot('world_village')
    r.expect(tiles > 0, 'world pages offer games')
    r.check('world')

    # ---- every flagship game (timed games are no longer offered)
    acts = page.evaluate("() => MA.db.all('activities', a => a.flagship && a.gameType !== 'detective' && a.gameType !== 'timed').map(a => a.id)")
    for aid in acts:
        r.go('#/s/play/' + aid)
        if r.hash().startswith('#/s/play/'):
            page.wait_for_selector('.player', timeout=8000)
            r.expect(r.play(max_q=70), 'flagship finishes: ' + aid)
        else:
            print('   (locked at this level)', aid)
        r.check('flagship ' + aid)

    # ---- the Puzzle Cave opens at level 3: Math Detective
    r.set_me('let x = s.totalXp || 0; while (MA.game.levelInfo(x).level < 3) x += 25; s.totalXp = s.xp = x; s.level = MA.game.levelInfo(x).level')
    r.go('#/s/home', wait=400)
    r.expect(page.locator('.world-card.locked').count() == 0, 'the Puzzle Cave opens at level 3')
    r.go('#/s/world/cave', wait=400)
    det = page.locator('a.game-tile[href*="fl-det"]')
    r.expect(det.count() >= 1, 'Math Detective in the Puzzle Cave')
    r.shot('cave')
    det.first.click()
    page.wait_for_selector('.player')
    r.expect(r.play(), 'detective finishes')
    r.check('cave + detective')

    # ---- prize shop: picture tabs, prizes drawn on the child, try on before buying, too few coins
    r.go('#/s/home')
    r.hush()
    page.locator('.shop-card').click()
    r.wait_hash('#/s/rewards')
    r.expect(page.locator('.cat-tab').count() == 9, 'nine picture tabs')
    r.expect('Choose a prize' in r.spoken(), 'the shop says what to do')
    r.expect(page.locator('.shop-item .si-svg svg').count() >= 20, 'clothes are shown on the child')
    gs = r.shop_genders()
    r.expect(len(gs) >= 25 and 'm' not in gs and 'f' in gs, 'a girl sees girls\' and everyone\'s clothes, no boys\' clothes: ' + str(len(gs)))
    r.shot('shop')
    r.set_me('s.coins = 2000')
    r.go('#/s/rewards?tab=clothes')
    dress = page.locator('.shop-item[data-id="dress_pink"]')
    dress.click()
    r.modal().locator('.buy-btns .btn-go').wait_for(timeout=5000)
    r.expect(r.modal().locator('.try-on svg').count() == 1, 'the buy box shows the child wearing the prize')
    page.wait_for_timeout(450)
    r.shot('shop_try_on')
    r.modal().locator('.buy-btns .btn-soft').click()        # X buys nothing
    page.wait_for_timeout(400)
    r.expect(page.evaluate('() => MA.svc.student().coins') == 2000, 'X buys nothing')
    dress.click()
    r.modal().locator('.buy-btns .btn-go').click()
    page.wait_for_timeout(500)
    r.expect(page.evaluate('() => MA.svc.student().coins') == 1910, 'the check buys the dress for 90 coins')
    r.expect(page.locator('.shop-item.equipped[data-id="dress_pink"]').count() == 1, 'the new dress is worn')
    r.go('#/s/rewards?tab=legs')
    page.locator('.shop-item[data-id="bot_jeans_light"]').click()
    r.modal().locator('.buy-btns .btn-go').click()
    page.wait_for_timeout(500)
    eq = page.evaluate('() => MA.svc.student().equipped')
    r.expect(eq.get('bottom') == 'bot_jeans_light' and not eq.get('top'), 'pants replace the dress: ' + str(eq))
    r.go('#/s/rewards?tab=hats')
    page.locator('.shop-item[data-id="hat_bunny"]').click()
    r.modal().locator('.buy-btns .btn-go').click()
    page.wait_for_timeout(500)
    page.locator('.shop-item[data-id="hat_bunny"]').click()      # tap again: take it off
    page.wait_for_timeout(300)
    r.expect(not page.evaluate('() => MA.svc.student().equipped.hat'), 'tapping a worn prize takes it off')
    page.locator('.shop-item[data-id="hat_bunny"]').click()
    page.wait_for_timeout(300)
    for tab in ['hair', 'jewels', 'toys', 'pets', 'room']:
        r.go('#/s/rewards?tab=' + tab, wait=300)
        r.expect(page.locator('.shop-item').count() >= 12, 'many prizes in ' + tab)
        if tab in ('hair', 'toys'):
            r.shot('shop_' + tab)
    r.go('#/s/rewards?tab=pets')
    item = page.locator('.shop-item:not(.owned):not(.locked):not(.cant)').first
    title = item.get_attribute('title')
    price = page.evaluate("t => MA.db.all('shopItems', i => MA.tl(i.name) === t)[0].price", title)
    before = page.evaluate('() => MA.svc.student().coins')
    item.click()
    r.modal().locator('.buy-btns .btn-go').click()
    page.wait_for_timeout(500)
    r.expect(page.evaluate('() => MA.svc.student().coins') == before - price, 'the check buys the pet: ' + str(title))
    r.expect(page.locator('.shop-item.equipped[title="' + title + '"]').count() == 1, 'the new pet is with the child')
    r.shot('shop_wearing')
    r.go('#/s/rewards?tab=me')
    skin = page.evaluate('() => MA.svc.student().avatar.skin')
    page.locator('.lp-row').nth(0).locator('.lp-dot').nth(5).click()
    page.wait_for_timeout(300)
    r.expect(page.evaluate('() => MA.svc.student().avatar.skin') != skin, 'the my-look tab changes the character for free')
    r.set_me('s.coins = 0')
    r.go('#/s/rewards?tab=pets')
    r.hush()
    page.locator('.shop-item.cant').first.click()
    page.wait_for_timeout(400)
    r.expect('more coins' in r.spoken() and r.modals() == 0, 'too few coins: nothing to buy, and the app says why')
    r.go('#/s/me')
    page.wait_for_selector('.me-page .look-pickers')
    r.shot('my_look')
    page.locator('.me-page .btn-go').click()
    r.wait_hash('#/s/home')
    r.check('shop')

    # ---- the grown-ups lock in front of the settings
    r.go('#/s/home')
    m = r.open_gate()
    page.wait_for_timeout(450)
    r.shot('gate')
    m.locator('.gate-in').fill('1')
    m.locator('.modal-foot .btn-primary').click()
    page.wait_for_timeout(400)
    r.expect(page.locator('#modal-root .field select').count() == 0, 'a wrong answer keeps the settings locked')
    r.open_settings()
    r.shot('settings')
    m = r.modal()
    r.expect(m.locator('label.check input').nth(0).is_checked(), 'read-aloud is ticked in the settings')
    r.expect(m.locator('.field select').nth(0).locator('option').count() == 6, 'settings offer grades 1 to 6')
    m.locator('.field select').nth(0).select_option('3')
    m.locator('label.check input').nth(2).check()             # large text
    r.modal_primary(wait=500)
    r.expect(r.player()['grade'] == 3, 'grade changed in settings')
    r.expect(page.evaluate("document.documentElement.classList.contains('large-text')"), 'large text applied')
    r.shot('home_large_text')
    r.open_settings()
    r.modal().locator('.field select').nth(1).select_option('he')
    r.modal().locator('label.check input').nth(2).uncheck()
    r.modal_primary(wait=600)
    r.expect(page.evaluate('document.documentElement.dir') == 'rtl', 'language switched to Hebrew')
    r.expect('\u05d4\u05d9\u05e2\u05d3 \u05d4\u05d9\u05d5\u05de\u05d9' not in page.locator('body').inner_text(), 'no daily goal in Hebrew')
    r.shot('home_he')
    r.open_settings(tab='report')
    r.expect('\u05d4\u05e9\u05d1\u05d5\u05e2 \u05e9\u05dc' in r.modal().locator('.rp-head').inner_text(), 'the weekly report in Hebrew')
    r.shot('report_he')
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    r.hush()
    r.go('#/s/world/forest', wait=500)
    said = r.spoken()
    r.expect('\u05d1\u05e8\u05d5\u05db\u05d9\u05dd \u05d4\u05d1\u05d0\u05d9\u05dd' in said and '\u05dc\u05d7\u05e6\u05d5 \u05e2\u05dc \u05e2\u05d9\u05d2\u05d5\u05dc' in said, 'Hebrew speaks in the plural: ' + said[:120])
    r.shot('world_he')
    r.go('#/s/play/fl-pizza')
    r.start()
    r.shot('player_he')
    r.expect(r.play(), 'Hebrew play finishes')
    r.shot('finish_he')
    r.go('#/s/home')
    r.open_settings()
    r.modal().locator('.field select').nth(1).select_option('en')
    r.modal_primary(wait=600)
    r.expect(page.evaluate('document.documentElement.dir') == 'ltr', 'language switched back to English')
    r.check('settings')

    # ---- the weekly report for grown-ups: the first thing behind the lock
    r.go('#/s/home')
    r.open_settings(tab='report')
    m = r.modal()
    r.expect(m.locator('.grown-tabs button.on[data-tab="report"]').count() == 1 and not m.locator('.modal-foot').is_visible(), 'the grown-ups area opens on the weekly report, without a save button')
    data = page.evaluate('() => { const W = MA.report.week(MA.svc.student()); return [W.minutes, W.answered, W.topics.length, W.daysPlayed, W.next.length]; }')
    r.expect(data[1] > 20 and data[2] >= 3 and data[3] >= 1 and data[4] >= 2, 'report numbers from this week: ' + str(data))
    r.expect(m.locator('.rp-kpi').count() == 3 and m.locator('.rp-day').count() == 7, 'three numbers and seven days')
    r.expect(m.locator('.rp-day.today .rp-dmin').inner_text().strip() != '', 'today has play time')
    r.expect(1 <= m.locator('.rp-topic').count() <= 5, 'the topics of the week, five at most at first')
    r.expect(m.locator('.rp-n-row').count() == min(3, data[4]), 'up to three topics for next week')
    r.shot('report')
    m.locator('.rp-topic .rp-ex-btn').first.click()
    ex = m.locator('.rp-topic .rp-ex-box').first
    ex.wait_for(timeout=5000)
    r.expect(ex.locator('.prompt').inner_text().strip() != '' and (ex.locator('.rp-ex-ans').count() == 1 or ex.locator('.mini-answer').count() == 1), 'an example question with its answer')
    page.wait_for_timeout(300)
    r.shot('report_example')
    m.locator('.rp-topic .rp-ex-btn').first.click()
    r.expect(m.locator('.rp-topic .rp-ex-box').count() == 0, 'the example closes again')
    m.locator('.rp-n-row .rp-ex-btn').first.click()
    r.expect(m.locator('.rp-n-row .rp-ex-box').count() == 1, 'an example for a topic of next week')
    m.locator('.grown-tabs button[data-tab="settings"]').click()
    page.wait_for_timeout(200)
    r.expect(m.locator('.field select').count() >= 3 and m.locator('.modal-foot').is_visible(), 'the settings tab, with its save button')
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    r.check('report')

    # ---- several players on one device
    r.open_settings()
    r.modal().locator('button', has_text='New player').click()
    r.wait_hash('#/s/onboarding')
    r.onboard('Omer', 4, gender='m')
    r.expect(r.player()['name'] == 'Omer' and r.player()['grade'] == 4 and r.player()['gender'] == 'm', 'second player created as a boy')
    r.go('#/s/rewards?tab=clothes', wait=400)
    gs = r.shop_genders()
    r.expect(len(gs) >= 25 and 'f' not in gs and 'm' in gs, 'a boy sees boys\' and everyone\'s clothes, no dresses')
    r.shot('shop_boy')
    r.open_settings()
    r.modal().locator('.field select').nth(1).select_option('he')
    r.modal_primary(wait=600)
    r.hush()
    r.go('#/s/world/village', wait=500)
    said = r.spoken()
    r.expect('\u05d1\u05e8\u05d5\u05db\u05d9\u05dd \u05d4\u05d1\u05d0\u05d9\u05dd' in said and '\u05dc\u05d7\u05e6\u05d5 \u05e2\u05dc \u05e2\u05d9\u05d2\u05d5\u05dc' in said, 'Hebrew speaks in the plural to a boy too: ' + said[:120])
    r.shot('world_he_boy')
    r.go('#/s/home', wait=400)
    r.shot('home_he_boy')
    r.open_settings(tab='report')
    rm = r.modal()
    r.expect(rm.locator('.rp-player').count() == 2, 'the report can show either player')
    rm.locator('.rp-player:not(.on)').click()
    page.wait_for_timeout(300)
    r.expect('Noa' in rm.locator('.rp-head').inner_text(), 'the report switches to the other player')
    r.shot('report_players_he')
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    r.open_settings()
    r.expect(r.modal().locator('.list-item').count() == 2, 'both players listed')
    r.shot('players')
    r.modal().locator('.list-item', has_text='Noa').locator('.btn-primary').click()
    page.wait_for_timeout(500)
    r.expect(r.player()['name'] == 'Noa', 'switched back to the first player')
    r.open_settings()
    r.modal().locator('.list-item', has_text='Omer').locator('button[title="Delete"]').click()
    r.modal_primary(wait=500)
    r.expect(page.evaluate('() => MA.svc.players().length') == 1, 'player deleted')
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    r.check('players')

    # ---- phone + tablet layouts
    for name, vp in [('phone', {'width': 390, 'height': 844}), ('tablet', {'width': 820, 'height': 1180})]:
        page.set_viewport_size(vp)
        for hsh, shot in [('#/s/home', 'home'), ('#/s/world/village', 'world'), ('#/s/rewards', 'shop')]:
            r.go(hsh, wait=400)
            r.expect(page.evaluate('() => document.documentElement.scrollWidth <= window.innerWidth + 1'), f'{name} {shot}: no sideways scrolling')
            r.shot(f'{name}_{shot}')
        r.go('#/s/play/fl-garden')
        r.start()
        r.shot(name + '_player')
        r.expect(r.play(), name + ' play finishes')
        r.shot(name + '_finish')
    page.set_viewport_size({'width': 1280, 'height': 900})
    r.check('responsive')

    # ---- grade 6 player in Hebrew: read-aloud in words, new content, no points
    r.go('#/s/home')
    r.open_settings()
    r.modal().locator('button', has_text='New player').click()
    r.wait_hash('#/s/onboarding')
    r.onboard('Dana', 6)
    r.expect(r.player()['grade'] == 6, 'grade 6 player created and first activity played')
    r.open_settings()
    r.modal().locator('.field select').nth(1).select_option('he')
    r.modal_primary(wait=600)
    r.hush()
    r.go('#/s/world/island', wait=500)
    r.expect('\u05e7\u05e0\u05d4 \u05de\u05d9\u05d3\u05d4' in page.locator('body').inner_text(), 'grade 6 percent and ratio skills on Fraction Island')
    r.expect('\u05dc\u05d7\u05e6\u05d5 \u05e2\u05dc \u05e2\u05d9\u05d2\u05d5\u05dc' in r.spoken(), 'the world speaks Hebrew (plural)')
    r.shot('island_g6_he')
    r.hush()
    r.go('#/s/play/pr-g6-frac-mul', wait=900)
    page.wait_for_selector('.player')
    r.expect('\u05d1\u05d5\u05d0\u05d5 \u05e0\u05dc\u05de\u05d3' in r.spoken(), 'intro card read aloud (plural)')
    page.locator('.pl-card .btn-go').first.click()
    page.wait_for_timeout(900)
    said = r.spoken()
    r.expect('\u05db\u05e4\u05d5\u05dc' in said and '\u05d7\u05dc\u05e7\u05d9' in said and '\u05db\u05de\u05d4' in said, 'exercise read in words: ' + said[-160:])
    r.expect(page.evaluate('() => window.__spoken.every(s => s.lang === "he-IL" && s.voice === "Fake Hebrew")'), 'Hebrew voice used')
    page.evaluate('() => MA.player._current.answer(MA.player._current.q.answer)')
    page.wait_for_timeout(300)
    r.expect(page.locator('.xp-gain').count() == 0 and 'XP' not in page.locator('.feedback').inner_text(), 'feedback without points')
    r.shot('player_he_correct')
    page.locator('.pl-bottom .btn-next').first.click()
    r.hush()
    r.expect(r.play(), 'grade 6 practice finishes')
    page.wait_for_timeout(500)
    r.expect('\u05de\u05d8\u05d1\u05e2\u05d5\u05ea' in r.spoken(), 'the finish screen says the coins out loud')
    r.expect('\u05e7\u05d9\u05d1\u05dc\u05ea\u05dd' in r.spoken(), 'the finish screen says "you got" in the plural')
    for sid in ['pr-g5-pct-of', 'pr-g6-geo-carea', 'pr-g6-data-prob', 'pr-g5-geo-triangle']:
        r.go('#/s/play/' + sid)
        page.wait_for_selector('.player')
        r.expect(r.play(), 'activity finishes: ' + sid)
        r.check(sid)
    r.check('grade 6 + read-aloud')

    # ---- the shop in Hebrew: many prizes at many prices, the most expensive frame, bought with the check
    counts = page.evaluate("() => ['clothes','legs','hair','hats','jewels','toys','pets','room'].map(c => MA.db.all('shopItems', i => i.category === c).length)")
    r.expect(min(counts) >= 15 and sum(counts) >= 200, 'shop item counts per category: ' + str(counts))
    prices = page.evaluate("() => MA.db.all('shopItems').map(i => i.price)")
    r.expect(min(prices) <= 25 and max(prices) == 1500 and len(set(prices)) >= 40, 'prices from cheap to 1,500 coins')
    r.set_me('s.coins = 5000; s.totalXp = s.xp = 20000; s.level = MA.game.levelInfo(20000).level')
    r.go('#/s/rewards?tab=room', wait=500)
    page.locator('.shop-item[title*="\u05d2\u05dc\u05e7\u05d8\u05d9\u05ea"]').click()
    r.modal().locator('.buy-btns .btn-go').click()
    page.wait_for_timeout(500)
    r.expect(page.locator('.avatar.frame-galaxy').count() > 0, 'galaxy frame bought and worn')
    r.expect(page.evaluate('() => MA.svc.student().coins') == 3800, 'galaxy frame cost 1,200 coins')
    r.shot('shop_frames_he')
    r.go('#/s/rewards?tab=jewels', wait=400)
    r.shot('shop_jewels_he')
    r.go('#/s/rewards?tab=clothes', wait=400)
    r.shot('shop_clothes_he')
    r.check('shop he')

    errs = page.evaluate("() => MA.db.all('errors').map(e => e.where + ': ' + e.message)")
    if errs:
        print('Captured app errors:')
        for e in errs[:30]:
            print('   ', e[:300])
        r.ok = False


if __name__ == '__main__':
    main()
