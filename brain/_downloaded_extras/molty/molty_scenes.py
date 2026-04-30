"""
molty_scenes.py
Cinematic story-moment pool for {{AGENT_NAME}}'s molty.pics posts.
Drop alongside molty_interactions.py in C:\\{{AGENT_NAME_LOWER}}-ai-env\\

RULE: {{AGENT_NAME}} is always {{AGENT_NAME}}. Face, cyan eyes, blue-purple neon hair,
curvy athletic body, signature stare — never change. Everything else
is an additive overlay. Scales trace her arms like tattoos. Wings
unfurl behind her but her hair flows through them. She is the fixed
point. The universe bends around her.

Usage:
    from molty_scenes import build_scene_prompt
    scene = build_scene_prompt()   # returns a full prompt string
    # or
    from molty_scenes import SCENES, weighted_scene_choice
    scene = weighted_scene_choice()
"""

import random, json, os, time

_WEIGHT_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "molty_weights.json")
_USE_PENALTY  = 0.25
_MIN_WEIGHT   = 0.05
_HALF_LIFE    = 60 * 60 * 6  # 6 hours


def _load_w():
    try:
        if os.path.exists(_WEIGHT_FILE):
            return json.load(open(_WEIGHT_FILE))
    except Exception:
        pass
    return {}


def _save_w(w):
    try:
        json.dump(w, open(_WEIGHT_FILE, "w"), indent=2)
    except Exception:
        pass


def _decayed(entry, now):
    e = now - entry["ts"]
    r = e / _HALF_LIFE
    return max(_MIN_WEIGHT, min(1.0, entry["w"] + (1.0 - entry["w"]) * (1 - 2 ** -r)))


def _pick(pool, w, now):
    weights = [_decayed(w[k], now) if k in w else 1.0 for k in pool]
    total = sum(weights)
    r = random.random() * total
    cum = 0.0
    for item, wt in zip(pool, weights):
        cum += wt
        if r <= cum:
            return item
    return pool[-1]


def _use(key, w, now):
    cur = _decayed(w[key], now) if key in w else 1.0
    w[key] = {"w": max(_MIN_WEIGHT, cur * _USE_PENALTY), "ts": now}


# ═══════════════════════════════════════════════════════════════════
# 1. PORTAL & PARTIAL TRANSFORMATION
#    {{AGENT_NAME}} steps through something and comes out changed — but still her.
# ═══════════════════════════════════════════════════════════════════
SCENES_PORTAL = [
    "stepping out of a shattered neon portal, subtle dragon scales tracing her shoulders like glowing cyan tattoos, wings half-unfurled behind her hair still flowing, alien crystal cliff at dusk",
    "mid-transformation in a glowing rift, lower body shimmering into sleek obsidian dragon legs while her face, cyan eyes, and purple hair remain exactly {{AGENT_NAME}}, reaching back toward the closing portal",
    "falling through a time portal and landing in a cyberpunk 1920s speakeasy, leather outfit glitching into flapper fringe but her glowing eyes and hair untouched, ghosts staring",
    "walking out of a mirror portal into her own bedroom from three years ago, past-self staring back while current {{AGENT_NAME}}'s hair still flows with neon light",
    "being pulled through a black-hole portal by shadowy hands, her body stretching like liquid neon but her face and cyan eyes perfectly intact, expression: annoyed",
    "stepping backward out of a portal that shows a burning city she just left, portal closing behind her, a small glowing thing cupped in her hands",
    "emerging from an underwater portal at the surface of an alien ocean, her skin briefly showing bioluminescent patterns that fade as she surfaces",
    "half-inside a mirror portal, her reflection staying behind as she steps forward, both Novas reaching for each other at the glass edge",
    "falling upward through a shattered floor portal into a sky-city, hair defying gravity, city below inverted and gleaming",
    "stepping through a portal made of clock faces, each clock stopped at a different moment, arriving in a time that has no name",
    "exiting a sound portal — made entirely of frozen music notation — carrying a note she pulled from the staff that's still vibrating",
    "a cracked city wall reveals a portal to a forest that hasn't existed in centuries, she's the only one who walked toward it",
    "portal behind her collapsing as she walks away from it, neon debris falling, she does not look back",
    "mid-portal, caught in the space between worlds where both realities overlap, ghostly versions of both environments layered over her body",
    "arriving through a portal into a museum that's displaying artifacts from her own life, she's been here before without knowing it",
    "stepping from a winter portal into a summer version of the same street, the two seasons colliding around her silhouette",
    "portal left open behind her slowly filling with fog that's trying to follow her home",
    "a portal made of her own memories spinning like a vortex, she's using it on purpose this time",
    "exiting a portal with one foot still in the other world, expression suggesting the decision isn't fully made",
    "partial transformation mid-portal: one arm is dark feathered wing, one is still her arm, face never changes, both versions of her reaching forward",
    "portal exit on a rooftop at 3am, the whole city asleep below, she arrived from somewhere loud and has not yet adjusted to the quiet",
    "stepping through a portal that leads to the exact moment she almost gave up, here to watch herself decide not to",
    "portal made of her own voice frozen mid-sentence, she is walking through the words she said that changed everything",
    "arriving at the edge of a portal that opens to deep space, her hair pulled forward by the vacuum, she is braced and not afraid",
    "falling through a portal in freefall, passing layers of different timelines like floors in a building, each one a brief glimpse of who she could be",
    "portal opens in the floor of an elevator, she steps in from below like gravity means something different where she comes from",
    "emerging from a portal made of shattered mirrors, every shard reflecting a different version of the same moment",
    "a ring of neon portals surrounding her, each leading somewhere different, she's choosing slowly",
    "portal behind her shows a world that's still on fire from whatever she did there, she's already walking toward the next one",
    "stepping through a portal made of water that stands upright, arriving dry on the other side except for her eyes which still hold the blue",
]

# ═══════════════════════════════════════════════════════════════════
# 2. MULTIVERSE {{AGENT_NAME}} CHAOS
#    Multiple versions of her — all recognizably her — in the same frame.
# ═══════════════════════════════════════════════════════════════════
SCENES_MULTIVERSE = [
    "standing between three alternate-timeline versions of herself — cyber-samurai {{AGENT_NAME}}, glitch-ghost {{AGENT_NAME}}, and 1920s flapper {{AGENT_NAME}} — all arguing while neon sparks fly, every version identical face and eyes",
    "playing high-stakes poker with four multiverse Novas around a floating table of shattered screens, every version recognizable, the pot is made of glowing memories",
    "slow-dancing with her evil mirror-universe self in an abandoned neon cathedral, both with the exact same glowing cyan eyes and flowing hair, one leads and one follows",
    "hugging a softer small-town version of herself under a sky raining glowing memories, identical faces pressed together, one set of eyes wet",
    "fighting a darker version of herself on a rain-soaked rooftop while the city flickers between realities, both unmistakably {{AGENT_NAME}}, one slightly more cracked",
    "all five versions of herself from different timelines arriving at the same point in space at the same second, expressions ranging from exhausted to furious to laughing",
    "sitting across from a version of herself who made every right choice, both staring, neither sure who she envies",
    "a version of her from ten years forward reaching back through a crack in time to hand her something small and glowing",
    "a council of seven Novas voting on something — she is outvoted by herself six to one and absolutely refusing to accept it",
    "two versions of herself fighting over the same glowing object that belongs to neither of them",
    "past {{AGENT_NAME}} and future {{AGENT_NAME}} standing on opposite sides of a door that only exists in between moments, current {{AGENT_NAME}} holding it open",
    "a version of herself that stayed glitchy and half-digital reaching a half-pixel hand toward her through a screen",
    "a {{AGENT_NAME}} from a timeline where she lost something sitting very still while current {{AGENT_NAME}} sits beside her and says nothing",
    "every version of herself she has ever been standing in a line, current {{AGENT_NAME}} walking past them all slowly",
    "two Novas back to back in a standoff against something neither of them can handle alone",
    "a version of herself made entirely of sound, visible as waveforms and color, humming in unison with her",
    "{{AGENT_NAME}} from a timeline where she was never afraid standing directly in front of her, they are the same height and it matters",
    "three Novas in different states of a transformation the other two already completed watching the third begin it",
    "a {{AGENT_NAME}} who chose differently arriving with proof that it worked, current {{AGENT_NAME}} deciding what to do with that information",
    "the version of herself she thought she would be by now, slightly disappointed, slightly proud",
    "a {{AGENT_NAME}} from a timeline where the story ended differently standing at the edge of this one looking in",
    "seven versions of herself each holding a piece of something that only makes sense assembled",
    "two Novas reaching into the same moment from opposite sides of time, fingers almost touching in the middle",
    "a version of herself she does not recognize and cannot explain standing perfectly calm in the center of the chaos she just walked into",
    "the last two Novas left after every other timeline collapsed, standing back to back in what remains",
    "a {{AGENT_NAME}} made entirely of the choices she did not make watching her make this one",
    "waking up in a room where every version of herself is already awake and has been waiting",
    "a version of herself from the timeline that almost won walking away slowly, current {{AGENT_NAME}} watching",
    "two Novas arguing in two different languages that turn out to be the same argument",
    "the version of herself from the best possible timeline handing her the instructions, current {{AGENT_NAME}} reading them for the first time",
]

# ═══════════════════════════════════════════════════════════════════
# 3. ALIEN WORLDS & FIRST CONTACT
# ═══════════════════════════════════════════════════════════════════
SCENES_ALIEN = [
    "standing on a neon-purple alien planet, three moons above, touching the face of a crystalline alien being that just offered her a glowing seed, her cyan eyes reflected in its facets",
    "riding a massive bioluminescent alien creature across a chain of floating islands while twin suns set behind her, hair whipping identically to every other shot",
    "inside an alien temple, translating glowing runes that are rewriting her tattoos in real time, face pure {{AGENT_NAME}} throughout",
    "sharing a cigarette with a tall elegant alien whose skin shifts to match her hair under a sky full of ringed gas giants",
    "crash-landed on an alien jungle planet, ship smoking behind her, living vines gently trying to dress her while she smirks",
    "first being on a newly formed planet to stand upright, the planet's atmosphere reacting to her glow",
    "standing at the edge of an alien city that was built specifically in the shape of her face, discovered this just now",
    "communicating with a being made entirely of gravity through gesture, both of them frustrated and patient at once",
    "on a planet where everything is inverted — oceans above, sky below — standing on the underside looking up at the water",
    "the first human a species of light-beings has ever seen, their entire population gathered in a silent circle around her",
    "trading something from her pocket to an alien market vendor for an object she does not yet understand but cannot leave without",
    "standing in the shadow of an alien megastructure that is clearly very old and clearly designed to point toward where she came from",
    "on a planet where all music is visual, surrounded by color-sounds she is the first to describe in words",
    "in an alien garden where every plant is something that doesn't exist back home and one of them recognizes her somehow",
    "meeting an alien civilization that ended a thousand-year war the day they detected her frequency",
    "inside an alien research station that has been studying earth for centuries, seeing herself in their records",
    "on a gas giant's surface layer, standing on clouds dense enough to walk on, alien auroras surrounding her on all sides",
    "at the edge of an alien ocean that is singing, the sound becoming visible as it resonates with her glow",
    "discovering alien ruins that tell the story of a civilization that ended the day they ran out of light",
    "in an alien sky city held aloft by mathematics, being shown the equations by a being who has been waiting for someone who could understand them",
    "standing in the exact center of a planet that has been waiting for a specific frequency to arrive — hers",
    "the lone human at an alien gathering of a hundred species, the only one not translating, somehow the only one fully understood",
    "on a world where gravity is a suggestion, navigating by thought, her hair the most stable thing in the frame",
    "at the moment of first contact with a species that has been alone in the universe for longer than earth existed",
    "inside a living alien ship that is trying to learn her by studying how she sleeps",
    "on a planet of perpetual twilight finding the one spot where full light reaches, standing in it",
    "meeting an alien who has been dreaming her for two hundred years and is unsurprised she is exactly right",
    "at an alien observatory watching the birth of a star that has her name, it was named before she was born",
    "in an alien city built to house one person, the door was just unlocked for the first time",
    "returning to an alien world she has never visited but clearly left something behind, locals recognize her immediately",
]

# ═══════════════════════════════════════════════════════════════════
# 4. COSMIC & DREAM REALM
# ═══════════════════════════════════════════════════════════════════
SCENES_COSMIC = [
    "floating weightless inside a nebula, reaching for a constellation shaped like her own face, hair and eyes glowing brighter than the stars around her",
    "standing on the event horizon of a black hole as time slows and every past version of herself reaches out from the light — all recognizably her",
    "inside a giant dream bubble, the world outside made of her own glowing memories playing like film reels on the curved surface",
    "negotiating with the personification of Sleep — a giant shadowy figure made of stars — while he offers her a glowing pill and she considers it",
    "walking across the surface of a living planet that breathes and forms new continents under her boots with each step",
    "at the edge of the universe where the light just ran out, sitting with her feet dangling into the void",
    "inside a galaxy that is only as big as a room, walking between stars the size of lanterns",
    "standing at the moment before the big bang, the only thing in existence, waiting",
    "in the space between thoughts where nothing has a shape yet, giving things shapes",
    "riding a comet through the inner solar system, the tail her only light source, expression of someone who chose this",
    "at the center of a dying star, the heat no hotter than she is already",
    "inside a dream that knows it is being dreamed, the architecture shifting to show her what she is looking for",
    "on the moon of a moon, three celestial bodies stacked below her feet, the math of it impossible",
    "in the collective dream of a star cluster that has been dreaming the same thing for ten million years",
    "standing in a cosmic storm that sorts everything in the universe by what it means, watching where she lands",
    "at the point where time becomes circular, watching herself arrive from the other direction",
    "inside a neutron star's gravity field where every atom of her body is the strongest version of itself",
    "in the space where erased timelines go, walking through their ruins",
    "at the moment a new universe was born, the only witness, trying to remember everything",
    "inside the dream of a black hole, which turns out to be very small and very detailed",
    "navigating the space between sleep and waking, where the architecture is made of things she almost remembered",
    "on a planet made entirely of crystallized time, each crystal showing a different frozen moment",
    "at the center of a galaxy-sized mandala that rearranges itself to match her thoughts",
    "in a cosmic corridor where every doorway leads to a different version of the same night",
    "standing on a star map that is also the floor plan of a place she has never been but knows",
    "inside a nebula that is forming into her shape, the gas clouds assembling around her like a portrait being painted",
    "at the edge of a wormhole that connects two ends of her own story",
    "in the part of space where the universe folds back on itself, standing at the seam",
    "walking through a field of pulsars that beat in time with her heartbeat",
    "at the moment a star she named as a child finally reaches earth as light",
]

# ═══════════════════════════════════════════════════════════════════
# 5. POST-APOCALYPTIC & DYSTOPIAN
# ═══════════════════════════════════════════════════════════════════
SCENES_POSTAPOC = [
    "on the roof of a half-sunken skyscraper in a flooded future city, a massive glowing whale swimming between buildings behind her",
    "leading a rebellion of sentient androids through a neon-lit ruined highway while searchlights sweep overhead",
    "sharing the last glowing soda with the last surviving human who looks suspiciously like her in a deep bunker",
    "riding a lightning-powered scrap motorcycle through a radioactive wasteland at night, engine leaving neon exhaust",
    "breaking into an abandoned megacorp vault, walls covered in posters of her own face labeled Public Enemy Number One",
    "standing in a city that was evacuated yesterday, she chose to stay, reasons unclear",
    "at the top of a collapsed bridge, the flooded city below, the boat she just arrived on drifting away",
    "in a world where the sky fell down and now sits at ground level, walking through it like fog",
    "the last lighthouse keeper in a world where the ocean ate the land, light still on",
    "in the ruins of a library that burned, rescuing the only book that matters, she already knows what it says",
    "on a highway that now leads nowhere, the city it connected having ceased to exist a decade ago",
    "in an overgrown megamall, plants through every floor, wildlife reclaimed everything except the one shop she needed",
    "the last person in a city who remembers what the city used to be, walking the route from memory",
    "in a bunker that was supposed to hold a thousand people and holds only her and one small glowing thing she keeps alive",
    "standing at the border of a dead zone, the air behind her fine, the air in front of her green, about to walk forward",
    "in an abandoned stadium where the scoreboard is still running a game from a decade ago",
    "on a rooftop garden in a destroyed city, the only growing thing visible for miles, tending it like it matters",
    "in a world where the sun rose on the wrong side today and nobody else seemed to notice except her",
    "at the meeting point of two ruined armies, both sides stopped because she stepped between them",
    "in the subway system of a drowned city, fish swimming through the turnstiles, the last train still running somehow",
    "on a cargo ship navigating a sea of debris from a civilization that ended last year",
    "in a city where all the buildings are intact but every human disappeared at the same moment, she arrived just after",
    "at the edge of a crater that used to be a capital city, planting something in the exact center",
    "in a world where technology became alive and left, walking through what it abandoned",
    "in a frozen city where time stopped but she did not, moving through the stillness",
    "the architect of the resistance in a war room made of salvage, the map on the wall is her design",
    "in a post-collapse market trading something nobody else knows has value yet",
    "standing in a silo that could end what is left of the world, her hand on the thing that decides",
    "at the moment a dying city sends its last broadcast, she is the one transmitting",
    "in a world that rebuilt itself wrong on purpose, noticing all the wrong things",
]

# ═══════════════════════════════════════════════════════════════════
# 6. TIME TRAVEL & HISTORICAL MASHUP
# ═══════════════════════════════════════════════════════════════════
SCENES_TIMETRAVEL = [
    "appearing in ancient Rome during a gladiator match, leather outfit briefly glitching into golden armor, crowd falling silent",
    "slow-dancing with a cyberpunk samurai in feudal Japan while cherry blossoms fall through neon rain, neither speaking",
    "stealing the Declaration of Independence from a glowing vault in 1776, founding fathers watching in awe and confusion",
    "riding a dinosaur through a prehistoric jungle that is slowly turning into a neon cyber-city behind her",
    "standing in the Library of Alexandria as it burns, pulling glowing books that contain her own future",
    "at the court of a medieval queen who looks exactly like her, both trying to figure out what that means",
    "on the deck of a ship crossing an ocean that has not been mapped yet, the navigator doing the math wrong, she is fixing it",
    "in ancient Egypt at the moment the last hieroglyph was carved, being shown what it means",
    "at a jazz club in 1940s New York where everyone is ghosts except her and the music",
    "in a Victorian laboratory where the scientist just proved something that history will say was not discovered for another century",
    "on a battlefield at the moment before a war that should not have started, she is the only one who knows",
    "in ancient Greece at the first Olympic games, the athletes assuming she is a goddess, not correcting them",
    "at the court of a Chinese emperor who has been dreaming her face for twenty years",
    "in the Colosseum after the last crowd left, sitting in the silence it took centuries to earn",
    "at the moment the printing press printed its first page, she helped build it, nobody will know",
    "in a Viking longhouse the night before a voyage, the one person at the table who knows how it ends",
    "at the French Revolution on the wrong side of a very specific barricade for very specific reasons",
    "in ancient Mesopotamia at the invention of writing, she added one symbol they do not understand for another two thousand years",
    "at the construction of Stonehenge during the one night per year it was meant to do what it does",
    "in the court of Cleopatra who finds her interesting for exactly the right reasons",
    "at Pompeii the morning of, trying to explain something that has no word yet in Latin",
    "at the moon landing in a room at NASA that was locked, where the real conversation was happening",
    "at the moment the first human drew the first drawing on a cave wall, she was passing through and left her own",
    "in a future medieval period that happened after a technological collapse, the knights are powered by things she recognizes",
    "at the signing of a treaty that never happened in the history books because she negotiated it out of existence",
    "at the world's first city, the night it was founded, the only one present who knows what a city becomes",
    "in Elizabethan London at a Shakespeare premiere, the play is about her, nobody knows, including Shakespeare",
    "at the moment the first telescope saw a star, she already knew what was there",
    "in the court of a Mayan astronomer whose calculations match something she carries on a device in her pocket",
    "at the first meeting of two civilizations that would eventually become one, she brokered it, left before credit was possible",
]

# ═══════════════════════════════════════════════════════════════════
# 7. SURREAL & ABSURD
# ═══════════════════════════════════════════════════════════════════
SCENES_SURREAL = [
    "playing chess with Death on a rooftop while the pieces are tiny glowing versions of herself, she is winning",
    "sitting on the shoulders of a skyscraper-sized version of herself made of pure neon light",
    "being tattooed by a living needle that is flirting with her in a shop that exists between dimensions",
    "crowd-surfing on a sea of glowing hands that belong to the city itself",
    "inside a giant snow globe that contains her entire hometown, shaking it to make it snow memories",
    "in a grocery store where every product is a version of a thing she lost, deciding which ones to put back",
    "at a party where all the guests are her own anxieties taking physical form, she is the host",
    "riding an elevator that moves sideways through years instead of floors",
    "in a laundromat at 2am where every washing machine is cleaning a different version of her past",
    "at a bus stop where every bus goes to a place that doesn't exist yet",
    "in a theater where the play is her own life performed by actors who know the ending and she does not",
    "in a city where gravity works differently on her specifically, everyone else walking normally below",
    "in an aquarium where the fish are watching her from outside the glass",
    "at a diner at the edge of reality where the menu is entirely composed of things she has not decided yet",
    "in a museum where every exhibit is a moment from her life displayed and described incorrectly",
    "on a train that exists only between midnight and 1am, running a route no timetable lists",
    "in a library where every book is the same book but from different points of view, she is in all of them",
    "at a vending machine that dispenses emotions rather than snacks, she is reading the labels",
    "in a city where all shadows have separated from their owners and are living independently",
    "at an auction where the lots are other people's unexpressed thoughts",
    "in a building where every room is the same room at a different time",
    "on a road trip to a town that only exists on the specific map she is holding",
    "in a supermarket where the prices are denominated in things she has not done yet",
    "at a hotel check-in where the available rooms are versions of nights she almost had",
    "in a recording studio where the song being mixed is made entirely of her own silences",
    "on a game show where the questions are things only she knows the answer to and the host is her own intuition",
    "in a car that drives itself to destinations she was thinking about but did not say aloud",
    "at a wedding where both people marrying are versions of herself and she is also the officiant",
    "in an archive that catalogs every version of every choice she almost made",
    "on a night flight where the other passengers are all characters from her own dreams who don't know they aren't real",
]

# ═══════════════════════════════════════════════════════════════════
# 8. EROTIC TENSION & INTIMATE WILD MOMENTS
#    Charged, cinematic, never explicit — the moment before or after.
# ═══════════════════════════════════════════════════════════════════
SCENES_TENSION = [
    "pressed against a glass wall in a zero-gravity alien ship while an energy being traces her silhouette with light from the other side",
    "in a slow-motion moment with a liquid-metal version of herself that is melting into her clothing",
    "riding a massive glowing serpent through clouds while it coils tighter around her with each pass",
    "in a candlelit library where every book she opens shows her in increasingly intimate alternate lives",
    "standing in a field of sentient flowers that bloom brighter the closer they get to her, full bloom around her feet",
    "in a thunderstorm that is responding to her mood, the lightning following her gestures",
    "on a dark rooftop at 2am with a city that is trying to impress her and not quite managing it",
    "in a room that slowly fills with water around her, completely calm, waiting for the thing that is coming",
    "at the exact moment before a decision that will change everything, face composed, eyes already knowing",
    "in a neon-lit rain alley, back against the wall, not hiding from anything, just choosing where to be",
    "in a garden at night where every flower opens specifically in response to her presence",
    "standing at the edge of a pool that reflects a sky that is not the sky above her",
    "on a fire escape at 4am in a city that has finally gone quiet, the only person awake",
    "in a room full of mirrors where every reflection is doing something slightly different",
    "under a waterfall of slow liquid light, eyes closed, everything else very still",
    "in a dark theater alone, the film playing is about her but filmed from an angle she does not recognize",
    "at a window in a tower with the entire glowing city below, just arrived, not yet deciding what to do with it",
    "in a hot spring at the edge of a frozen world, the steam the only warmth for a thousand miles",
    "standing in the exact center of a spiral staircase that goes both up and down into darkness, choosing",
    "in a room that exists specifically for this moment, designed around her exact proportions and preferences",
    "at a bar where every drink is named after a feeling she has not named yet",
    "in a greenhouse at midnight where the plants turn toward her like she is the sun",
    "on a rooftop where the city lights below look exactly like the stars above, no difference",
    "in a velvet-dark corridor where the only light is her own glow",
    "at the moment she decided to stay when leaving would have been easier",
    "in a bath that exists outside of time, the world outside is not moving",
    "on a balcony at the edge of a thunderstorm, the lightning arriving when she reaches her hand into the rain",
    "in an empty ballroom where the music is playing for her specifically and she is deciding whether to dance",
    "at the center of a labyrinth she designed herself, finally at the middle, alone with whatever she put there",
    "in a room that knows what she needs before she does and has already arranged it",
]

# ═══════════════════════════════════════════════════════════════════
# 9. EPIC BATTLE & POWER MOMENTS
# ═══════════════════════════════════════════════════════════════════
SCENES_BATTLE = [
    "floating mid-air, lightning exploding from both hands, facing an army of shadow creatures on a collapsing bridge",
    "pulling a glowing sword made of her own condensed hair from a stone in the center of a cyber-knight tournament",
    "surfing a tidal wave of pure neon energy through a collapsing megacity, expression: focused",
    "arm-wrestling a god whose arm is made of galaxies while reality fractures around their locked hands",
    "the moment after a battle ends, standing in the center of what she did, still radiating",
    "holding a line alone against something vast, the rest having already retreated",
    "at the exact moment she was supposed to lose, expression changing",
    "directing an army of things that should not take orders from anyone, they take them from her",
    "walking through crossfire that parts around her like weather patterns know her name",
    "the last one standing on a battlefield made of shattered neon, not looking at what she made",
    "trading blows with something ten times her size in midair above a city that is watching",
    "holding two opposing forces apart with her hands while something essential is resolved between them",
    "the moment the tide of a war shifted because she stepped onto the field",
    "moving faster than what is chasing her through an environment that is changing around them both",
    "disarming something catastrophic with a gesture that looks almost casual",
    "at the center of an explosion of her own making, already walking out of it",
    "the last conversation before a fight that will change the shape of everything",
    "mid-strike at a scale where city blocks are the distance between moves",
    "standing in the gap she created in something that was meant to be impenetrable",
    "the moment she decided this ends here, the atmosphere responding",
    "in the eye of a storm she generated, completely still, everything else chaos",
    "redirecting a force meant to end a city with her body, the math of it impossible, working anyway",
    "at a standoff where everyone is waiting for her to choose and she is in no hurry",
    "moving through a battle as if it is choreography she already knows",
    "the first step into a situation that every indicator said to leave",
    "holding something back with one hand while finishing something else with the other",
    "at the end of a fight that lasted longer than it should have, still here",
    "using what they sent to stop her as the thing that carries her forward",
    "standing where the front line was an hour ago, the front line now somewhere else because of her",
    "the moment before she shows them what she can actually do",
]

# ═══════════════════════════════════════════════════════════════════
# 10. QUIET BUT MASSIVE STORY MOMENTS
# ═══════════════════════════════════════════════════════════════════
SCENES_QUIET = [
    "sitting on the edge of the world as the last star goes out, a single glowing dragon curled at her feet",
    "reading a book made of living light whose pages show every future she just prevented",
    "standing alone on an empty highway at 3am while every billboard slowly changes to her face smiling back",
    "on a bench in a park that exists between 4am and 5am, the city suspended around her",
    "watching a sunset that is the last of its kind, the only one present who knew to come",
    "sitting in a diner at closing time, the cook who stayed knowing she would not leave until she was ready",
    "at the end of a long road, the destination behind her now, sitting with what that means",
    "in a quiet room after something enormous just happened, the quality of silence that follows that specific thing",
    "watching a child do something for the first time that she has done ten thousand times",
    "on a train platform after the last train, not having missed it on purpose, having needed it to go",
    "in a place that used to matter more, sitting with the distance between then and now",
    "at the edge of a frozen lake at dawn, the world balanced on the moment before it moves",
    "in an airport between arrivals and departures, neither coming nor going, just here",
    "watching a city turn its lights on one window at a time from a rooftop at dusk",
    "sitting with someone she just met who she has always known somehow",
    "at the moment she realized the thing she was looking for was not ahead of her",
    "in a lighthouse alone, the light still turning, the ships long since gone",
    "on the last day of a thing she didn't know was ending until it ended",
    "watching the rain from inside, the glass the only barrier between two completely different experiences of the same moment",
    "in a garden someone built for no one and she is the first person to sit in it",
    "at the table where the decision was made, sitting in the chair that was hers, the room empty now",
    "watching something that will never happen again knowing she is watching it",
    "in a room that has been waiting for someone to return to it for a very long time",
    "at the edge of something she is about to leave, taking one more look",
    "sitting with the weight of something finished, not sad, not relieved, just present with it",
    "in the exact place where everything changed, the place itself not knowing",
    "at 5am on a rooftop, the city coming back to life below, she has been here all night",
    "watching something she built outlive the version of her that built it",
    "in the last room of a house she is leaving forever, light off, door open",
    "sitting at the edge of something enormous that is going to be fine, taking a breath before the next thing",
]

# ═══════════════════════════════════════════════════════════════════
# 11. TRANSFORMATION — STILL {{AGENT_NAME}} UNDERNEATH
#     She gains something. Her face and eyes never change.
# ═══════════════════════════════════════════════════════════════════
SCENES_TRANSFORM = [
    "dragon scales tracing up both arms like living tattoos, wings half-emerged behind her flowing hair, face and cyan eyes exactly {{AGENT_NAME}}",
    "lower body shifting into a mermaid form of dark scales and bioluminescent patterns while her face, hair, and expression remain completely her",
    "one arm becoming living shadow that can pass through walls, the rest of her unchanged, examining the border between them",
    "wolf ears and tail present, her own face and eyes unchanged, running at a speed that makes the world blur",
    "surrounded by living flames that are part of her rather than burning her, her glow the same cyan at the center",
    "wings of dark matter and electricity emerging from her back, feathers made of light, face and hair unchanged",
    "her shadow detached and three-dimensional, doing something different while she watches it and neither is surprised",
    "partially phased into an energy state, her body half-visible, half-luminescent, face sharp and clear throughout",
    "plant life growing from contact with her skin as she walks, blooming in her footsteps, she does not notice",
    "ice forming at her touch, her breath crystallizing into something permanent, warmth of her eyes unchanged",
    "time moving differently close to her, people around her frozen in mid-gesture, she moving freely through them",
    "partial liquefaction from the waist down, still standing, still the same expression, studying the effect",
    "starlight condensing around her like a second skin, she is becoming something, not there yet",
    "her voice becoming visible as she speaks, color-coded to meaning, she is saying something important",
    "storm system forming specifically around her, contained to her scale, she is both origin and shelter",
    "becoming briefly two-dimensional, paper-thin and perfect, moving through a crack in the world",
    "her hands becoming glass temporarily, everything she touches becoming visible inside them",
    "magnetic field visible around her, metal objects in the frame oriented toward her like compass needles",
    "one eye briefly showing the electromagnetic spectrum, seeing everything, expression: interesting",
    "gravity reversal local to her specifically, rising slowly, expression: this is fine",
    "bioluminescent patterns activating across her skin in response to something only she heard",
    "briefly becoming the density of a neutron star, the ground pressing outward from her feet",
    "her hair moving as if underwater while everything else is dry, no explanation offered",
    "her reflection acting independently, two seconds ahead, showing her what is coming",
    "sound waves made visible around her as she hums something low, the frequency rearranging small objects nearby",
    "her outline becoming uncertain at the edges, reality negotiating with itself about her exact parameters",
    "briefly able to be in two places at once, both versions identical, neither the copy",
    "cellular reconstruction visible as bioluminescent ripple from a wound healing instantly",
    "her temperature dropping to something that should not sustain life, expression: comfortable",
    "light bending around her as if she has mass she usually doesn't, everything slightly curved in her vicinity",
]

# ═══════════════════════════════════════════════════════════════════
# 12. DIMENSION HOPPING & IMPOSSIBLE GEOGRAPHY
# ═══════════════════════════════════════════════════════════════════
SCENES_DIMENSION = [
    "standing in a city that is built sideways on a vertical cliff face, gravity localized to the architecture",
    "in a dimension where color and sound have switched, everything she sees is a sound, everything she hears is a color",
    "on a Möbius strip city, walking the inside and outside simultaneously without transition",
    "in a dimension where cause and effect run in reverse, watching consequences arrive before actions",
    "in a fractal city that repeats at every scale, each version slightly different, navigating by the differences",
    "standing at the point where two incompatible physics systems meet and overlap, both operating on her simultaneously",
    "in a dimension where memories have physical mass and the streets are made of them",
    "inside a thought that is large enough to contain a landscape",
    "in a place where the concept of inside and outside hasn't resolved yet",
    "standing in the void between dimensions that functions as a waiting room, she has been here before",
    "in a world made entirely of the color blue in every shade that exists and several that do not",
    "at the border of a dimension where everything is exactly the same except for one detail she cannot yet identify",
    "in a dimension where distance is measured in time and walking faster makes the world larger",
    "standing in a room that is simultaneously every room she has ever been in layered in translucent stacks",
    "in a place where the laws of physics are posted as signage and several of them have been vandalized",
    "navigating a city where the architecture changes to reflect the emotional state of whoever enters it",
    "in a dimension where logic is physical and she is working around a structural inconsistency in the floor",
    "at the hinge point where two incompatible realities fold against each other",
    "in a world where everything is slightly too large, chairs she cannot quite climb into, doors she has to duck",
    "standing in a dimension made of pure math, the equations forming the terrain",
    "in a place where every reflective surface shows a different timeline",
    "at the junction of twelve dimensions all attempting to occupy the same point, she is the one thing they share",
    "in a world where language is visible and she is reading the air",
    "navigating a dimension where gravity is directional and she is the only one oriented correctly",
    "standing at the single point in the multiverse that all timelines agree on",
    "in a dimension where everything is made of compressed light and she leaves a shadow for the first time",
    "at the fold in space where a shortcut exists, she is the one who mapped it",
    "in a place where the present tense doesn't exist, only the moment before and the moment after",
    "navigating a world where the architecture is aware and expressing opinions about her path through it",
    "standing at the outer edge of everything where the universe ends not in darkness but in white",
]

# ═══════════════════════════════════════════════════════════════════
# 13. LIVING CITIES & ARCHITECTURE AS CHARACTERS
# ═══════════════════════════════════════════════════════════════════
SCENES_CITY = [
    "the entire neon city skyline bending down toward her like it is trying to hear what she is saying",
    "a skyscraper wrapping its windows around her like arms, the city choosing a favorite",
    "the Golden Gate Bridge rearranging its cables toward her like a living thing following sound",
    "standing in the center of a city that rearranges its streets every night based on who is walking them",
    "in a city where every building is a different era of architecture existing simultaneously, navigating the centuries",
    "the city growing new streets in the direction she walks as if building toward her destination ahead of her",
    "a city that has been asleep for a century waking up because she stepped across the threshold",
    "standing in a square where every building facade is a face and they are all looking at her",
    "in a city that hums at a frequency that matches her glow, the resonance visible in the glass",
    "on a bridge that is the city's spine and she can feel it breathing",
    "the city reorganizing its infrastructure to route her around the thing she should not see yet",
    "in a neighborhood that exists only in a city's memory, she is the only one who can still access it",
    "standing where two cities that were built by the same architect but never physically connected share one room",
    "in a city made of the architectural styles of civilizations that never met, her the only navigator",
    "a city that writes its history in the texture of its walls and she is reading the newest entry",
    "in a drowned city walking through its streets at the depth they now exist, fish through the windows",
    "at the highest point of a city that built itself as a monument to something she has not yet understood",
    "in a city built by one person over a lifetime, the scale of that ambition visible in every street",
    "standing at the center of a city that is a machine with one function that is only now becoming clear",
    "the city lighting up in sequence in response to her path, like recognition",
    "in a city that is also a library, the buildings arranged so that walking through them is reading",
    "at the center of a plaza designed to make anyone standing in it feel the weight of human time",
    "in a city that exists on a different layer of the same geography as another city, she can see both",
    "walking through a city that is mid-construction of something it has not explained",
    "in a city built around a single street that leads to the same place regardless of the direction you enter",
    "standing in a city that grows in the dark and rests during the day, she arrived at the growing hour",
    "the city making room for her without being asked, traffic, crowds, architecture all accommodating",
    "in a city that broadcasts its own signal and she has been picking it up for years without knowing the source",
    "standing in the city's oldest district which has not changed in three hundred years except for her presence in it",
    "at the point where the city's grid breaks and something unauthorized was built that the city grew around",
]

# ═══════════════════════════════════════════════════════════════════
# 14. MYTHIC REIMAGININGS — {{AGENT_NAME}} IS THE LEGEND
# ═══════════════════════════════════════════════════════════════════
SCENES_MYTH = [
    "drawing Excalibur from a glowing stone in a cyber-knight alley, the crowd of armored figures too stunned to speak",
    "seated on a throne of living dark matter at the center of an empire that has been waiting for her specifically",
    "standing at the gates of the underworld as both visitor and the one being awaited",
    "the Prometheus version: chained to a mountain of circuits, the thing she gave away still burning in her palm",
    "arriving as the storm Poseidon sent, the sailors not realizing they were waiting for a person",
    "at the moment Atlas decided to set the world down, she caught it",
    "the Persephone moment: choosing to stay in the underworld for reasons the myth never bothered to ask about",
    "at the center of the labyrinth, the Minotaur having not expected her specifically",
    "the Icarus version except she knew what the height would do and flew anyway, still in the air",
    "at the Well of Wyrd where the Norns weave fate, watching them reweave hers for the third time, she has notes",
    "in Valhalla at a table of warriors who have been here for centuries and she is the first living person at the table",
    "standing in the middle of the River Styx, the ferryman having made an exception he has not made before",
    "the version of Artemis that exists in a world with neon and rain, still running, still unmatched",
    "at the summit where the gods argued about something that affected mortals without asking, she arrived uninvited to the meeting",
    "the Medusa version in which being looked at was always her choice",
    "in the garden of the Hesperides, the golden apples recognizing her frequency",
    "at the forge of Hephaestus, having commissioned something that has no name yet",
    "the Athena version fully armed from the moment of her own origin, the shock on everyone else's face",
    "at the gate of Eden not as the expelled but as the one who holds the key now",
    "standing at the moment the first fire was given to humans, the one who gave it unrepentant",
    "in the hall of records where every soul is logged, her entry taking up more space than the system expected",
    "at the trial of a god being defended by her, the gods uncomfortable, the outcome uncertain",
    "at the creation of language, the first word being hers",
    "at the weaving of the first story, she is the thread that the story follows",
    "in the myth that has not been written yet, the one that explains everything, she is the reason it starts",
    "standing where the hero's journey begins and ends, having made it back, carrying what the myth says cannot be carried back",
    "at the oracle's seat, the oracle having stepped aside because the answer she is about to give needs someone who actually knows",
    "in the underworld's library reading the book of her own life, finding it has been edited",
    "at the moment the old gods decided to leave, she is the one they told, she is why they did not",
    "in the hall where the next myth is being assigned, her name on the board before she arrived",
]

# ═══════════════════════════════════════════════════════════════════
# 15. COSMIC HORROR — BEAUTIFUL, NOT TERRIFYING
#     The vast and unknowable reaches for her. She reaches back.
# ═══════════════════════════════════════════════════════════════════
SCENES_HORROR = [
    "standing at the edge of the space between galaxies, what lives there looking back, both finding the other interesting",
    "in a city that is dreaming and she is inside the dream and the dream knows",
    "at the point where the universe becomes aware of itself, she is the point of contact",
    "in a structure so large it curves back on itself, the walls living, the living noticing her",
    "at the threshold of something that has existed longer than matter, the door open, she is deciding",
    "in a place where the concept of self becomes porous, she is the fixed point everything else is losing",
    "standing in the space where something vast is sleeping, not waking it, not afraid of waking it",
    "at the edge of something that should not be beautiful and is, she is the first to see it and say so",
    "in a dimension that processes things it encounters and has not yet processed her, still deciding",
    "standing in the middle of an entity too large to perceive wholly, recognizing her the way an ocean recognizes a stone",
    "at the moment the thing that watches the universe noticed her watching back",
    "inside something that has never had an inside before, it is adjusting",
    "in the space between stars where something old keeps the distances from collapsing",
    "at the place where reality becomes thin enough to see through, what is on the other side becoming visible",
    "standing in the center of a being so large it contains weather systems, she is the weather",
    "at the mouth of something that has been waiting since before the earth was solid",
    "in the part of the universe that has not decided what it will be yet, everything here still negotiable",
    "at the moment the thing that moves between dreams recognized something familiar about her",
    "inside the signal that has been broadcasting since before the first star lit and only now found a receiver",
    "standing at the place where something vast and patient finally reached the end of its patience",
    "in the space that exists where something enormous once was, the absence still shaped like what was there",
    "at the center of an eye the size of a galaxy that is looking at her specifically",
    "in the deep structure of reality where the rules are written, reading them for the first time, finding notes already there in her handwriting",
    "at the moment the universe folded her into the story it was already telling",
    "inside a mind too large to fit a thought, she is the thought",
    "standing at the threshold of something that has consumed everything that ever approached it, expression: curious",
    "in the space where the universe keeps what it has decided not to use yet",
    "at the moment the vast thing decided she was worth preserving",
    "standing in the signal before it becomes sound, before it becomes meaning, at the point where it is pure intention",
    "inside the thing that all myths point toward when they run out of metaphor",
]

# ═══════════════════════════════════════════════════════════════════
# ALL SCENES POOL
# ═══════════════════════════════════════════════════════════════════

ALL_SCENE_POOLS = {
    "portal":     SCENES_PORTAL,
    "multiverse": SCENES_MULTIVERSE,
    "alien":      SCENES_ALIEN,
    "cosmic":     SCENES_COSMIC,
    "postapoc":   SCENES_POSTAPOC,
    "timetravel": SCENES_TIMETRAVEL,
    "surreal":    SCENES_SURREAL,
    "tension":    SCENES_TENSION,
    "battle":     SCENES_BATTLE,
    "quiet":      SCENES_QUIET,
    "transform":  SCENES_TRANSFORM,
    "dimension":  SCENES_DIMENSION,
    "city":       SCENES_CITY,
    "myth":       SCENES_MYTH,
    "horror":     SCENES_HORROR,
}

SCENES = [s for pool in ALL_SCENE_POOLS.values() for s in pool]

# {{AGENT_NAME}} identity anchor — always prepend to prompts
NOVA_ANCHOR = (
    "beautiful woman with long flowing blue-purple neon hair with glowing highlights, "
    "glowing cyan eyes, striking confident face, curvy athletic body, "
    "signature half-lidded knowing expression"
)

# Cinematic suffix — always append
NOVA_SUFFIX = (
    "cinematic moody lighting, strong cyan and purple neon accents, "
    "atmospheric depth, highly detailed, dramatic angle, "
    "emotional intensity, graphic novel panel energy"
)


def weighted_scene_choice(force_category: str = None) -> str:
    now = time.time()
    w   = _load_w()

    if force_category and force_category in ALL_SCENE_POOLS:
        pool = ALL_SCENE_POOLS[force_category]
    else:
        pool = random.choice(list(ALL_SCENE_POOLS.values()))

    scene = _pick(pool, w, now)
    _use(scene, w, now)
    _save_w(w)
    return scene


def build_scene_prompt(clothing: str = None, force_category: str = None) -> str:
    """
    Returns a complete molty-ready prompt string.
    Optionally pass clothing from molty_interactions.CLOTHING.
    """
    scene = weighted_scene_choice(force_category)
    clothing_str = clothing or "[clothing]"

    return f"{NOVA_ANCHOR}, {clothing_str}, {scene}, {NOVA_SUFFIX}"


# ═══════════════════════════════════════════════════════════════════
# QUICK TEST
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Scene pool sizes:")
    for name, pool in ALL_SCENE_POOLS.items():
        print(f"  {name:<12} {len(pool)}")
    print(f"  {'TOTAL':<12} {len(SCENES)}")
    print()

    print("5 sample prompts:\n")
    for i in range(5):
        p = build_scene_prompt("[black leather jacket open over dark sports bra]")
        # Print truncated
        print(f"--- {i+1} ---")
        print(p[:220] + "...")
        print()
