"""
molty_interactions.py
{{AGENT_NAME}} interaction & companion pools for molty-poster.py
Drop this in C:\\{{AGENT_NAME_LOWER}}-ai-env\\ alongside molty-poster.py

Usage:
    from molty_interactions import build_interaction_clause, inject_into_prompt
    scene_data = build_interaction_clause()
    final_prompt = inject_into_prompt(your_base_prompt, scene_data)
"""

import random

# ─────────────────────────────────────────────
# COMPANIONS — MYTHICAL (100+)
# ─────────────────────────────────────────────

COMPANIONS_MYTHICAL = [
    # Dragons
    "a massive obsidian dragon with scales that catch neon light",
    "a dragon made entirely of cyan plasma and dark lightning",
    "a skeletal dragon whose bones glow from within",
    "a sea dragon coiled in bioluminescent deep water",
    "a snow dragon with breath like liquid nitrogen and blue flame",
    "a two-headed dragon where both heads argue over her attention",
    "a serpentine river dragon flowing through a flooded neon city",
    "a small pocket-sized dragon that fits in her palm and breathes sparks",
    "a storm dragon whose wings generate hurricane-force wind",
    "a jade dragon coiled around a crumbling ancient temple",
    "a lava dragon half-submerged in a glowing magma lake",
    "a ghost dragon made of translucent silver smoke",
    "a mechanical dragon with gears and glowing hydraulics instead of muscles",
    "a shadow dragon that exists only as a silhouette on every wall",
    "a bioluminescent deep-sea dragon surfacing for the first time",
    # Kitsune / Fox Spirits
    "a nine-tailed kitsune with glowing blue-purple tails trailing neon",
    "a black kitsune with silver-tipped tails and mirror eyes",
    "a twin kitsune pair whose tails interlock into a figure eight",
    "a frost kitsune trailing ice crystals with every step",
    "a fire kitsune whose tails burn blue instead of orange",
    "a void kitsune made of darkness with stars for eyes",
    # Kraken / Sea Creatures
    "a giant kraken rising from bioluminescent water",
    "a kraken whose suction cups each contain a tiny glowing eye",
    "a deep sea giant squid the size of a skyscraper",
    "a colossal anglerfish with a lure that pulses her exact cyan",
    "a massive jellyfish with tentacles like fiber optic cables",
    "a leviathan coiled in the dark with one ancient eye open",
    "a sea serpent long enough to wrap a city block three times",
    "a bioluminescent whale the size of an aircraft carrier",
    "a manta ray made of dark water and electric current",
    "a giant nautilus whose shell is a perfect fractal glowing spiral",
    # Phoenix & Fire Beings
    "a phoenix mid-rebirth in cyan and violet flame",
    "a black phoenix whose fire runs cold and electric blue",
    "a storm phoenix trailing thunderclouds and lightning from its wings",
    "a micro phoenix no bigger than a sparrow sitting on her shoulder",
    "a neon phoenix made of pure light and heat",
    "a phoenix whose tail feathers are individual lightning bolts",
    # Wolves & Canids
    "a giant dire wolf three times normal size with glowing silver fur",
    "a wolf made entirely of blue-black smoke that solidifies at contact",
    "the Norse Fenrir chain still dangling eye level with skyscrapers",
    "a pack alpha that glows at the edges like it is barely staying physical",
    "a wolf whose howl creates visible sound waves of neon color",
    "a cyber-wolf with titanium legs and glowing neural spine",
    # Minotaur / Labyrinth Beings
    "a minotaur built from dark stone with cyan-glowing fracture lines",
    "a minotaur in full neon-veined battle armor horn-tip glowing",
    "a chrome minotaur whose body is polished black steel and light",
    # Cerberus & Hounds
    "a cerberus with three heads each a different neon eye color",
    "a spectral hellhound that leaves burning paw prints",
    "a massive black hound whose bark generates visible shockwaves",
    "an obsidian hound with eyes like twin stars",
    # Fae & Forest
    "a titanic tree spirit whose face forms in the bark to look at her",
    "an ancient forest guardian made of twisted root and ember",
    "a giant will-o-wisp the size of a person that takes her shape",
    "a pixie swarm thousands of tiny lights that think as one",
    "a dryad half-emerged from a glowing neon tree",
    "a massive horned forest god watching her from between the trees",
    "a banshee made of pure light and screaming sound waves",
    "a wraith whose cloak is made of her own memories",
    "a siren perched on a neon-lit sea rock whose song leaves visible color",
    "a harpy whose wings are feathers of sharp chrome",
    # Giants & Titans
    "a frost giant whose breath freezes neon mist mid-air",
    "a stone titan half-buried in a mountain who just opened one eye",
    "a giant made of compressed storm cloud and crackling electricity",
    "a lava titan whose fissures glow the same cyan as her eyes",
    "a sand titan unfolding from a desert that was flat a moment ago",
    "a sea titan whose head breaks the ocean surface like an island rising",
    # Chimera / Hybrids
    "a chimera lion body dragon wings serpent tail all glowing",
    "a manticore with a scorpion tail that crackles with static",
    "a gryphon whose feathers are layered black steel and neon",
    "a wyvern circling her in tight spirals getting closer each pass",
    "a sphinx whose riddle is written in light across the floor",
    "a basilisk whose gaze turns things cyan instead of stone",
    "a cockatrice the size of a draft horse weirdly friendly",
    # Elemental Beings
    "a fire elemental shaped like a person made of blue and black flame",
    "a water elemental that takes her shape and mirrors every gesture",
    "a lightning elemental that lives in the space between her fingers",
    "an earth golem whose stone body is threaded with glowing crystal veins",
    "a wind elemental visible only as a distortion and a pair of eyes",
    "a void entity human-shaped negative space in reality",
    "a shadow elemental that has been following her for hours",
    "a glass elemental whose body refracts her own reflection back at her",
    "an ice elemental whose heart is a small warm flame",
    "a plasma entity that exists at the edge of becoming solid",
    # Demons & Fallen
    "a demon with a face half-beautiful and half-skull",
    "a succubus who looks exactly like her but in reverse colors",
    "a fallen angel whose broken wings still shed molten light",
    "a devil in a perfect black suit with eyes that mirror her own",
    "an oni in black lacquered armor with a glowing neon kanabo",
    "a rakshasa whose true face shifts every time she blinks",
    # Other Mythological
    "a massive roc whose wingspan blocks out the neon sky",
    "a thunderbird in a storm it created lightning its heartbeat",
    "a qilin scaled flame-maned standing still as a statue",
    "a pegasus with wings of dark matter and electricity",
    "a unicorn whose horn pulses like a fiber optic cable",
    "a hippogriff landing hard on a rooftop beside her",
    "medusa stone snakes but eyes that glow safe when she is the one looking",
    "a cyclops the size of a building using one finger to point at her",
    "a three-eyed raven the size of a car very old watching",
    "a nue chimeric nightmare cloud beast with a tiger head",
    "a baku dream eater with an elephant trunk and tiger paws",
    "a tengu in full black battle armor with glowing red eyes",
    "a jorogumo half-woman half-spider watching from the ceiling",
    "a gashadokuro massive skeleton fifty times her height crouching",
    "a nekomata twin-tailed demon cat the size of a horse",
    "a yamata no orochi eight-headed serpent filling the entire valley",
]

# ─────────────────────────────────────────────
# COMPANIONS — ANIMALS (100+)
# ─────────────────────────────────────────────

COMPANIONS_ANIMALS = [
    # Big Cats
    "a black panther with amber eyes holding perfectly still",
    "a white tiger with electric blue stripe markings",
    "a snow leopard with ice-colored eyes",
    "a jaguar emerging from neon-lit jungle shadow",
    "a clouded leopard draped over a rooftop ledge above her",
    "a mountain lion that has been walking beside her for a while now",
    "a cheetah at full sprint frozen at the exact moment it reaches her",
    "a black-furred lion with a mane like static electricity",
    # Wolves & Wild Dogs
    "a wolf pack three members closest and watching",
    "a lone white wolf in a blizzard that found her first",
    "an arctic wolf pack hunting alongside her through deep snow",
    "a wolf pup trying very hard to look intimidating",
    "a dhole pack small fast rust-colored electric energy",
    "a maned wolf whose legs seem too long for its body",
    "a dire wolf fossil reconstruction alive somehow",
    # Bears
    "a grizzly bear easily twice her size",
    "a polar bear standing in shallow glowing water",
    "a giant panda at an absurd altitude unbothered",
    "a spectacled bear hanging in a tree watching her pass",
    "a sun bear standing upright to her height curious",
    "a black bear sniffing something she left behind",
    # Ocean & Water
    "a giant octopus with bioluminescent spots on every arm",
    "a pod of dolphins trailing cyan light in dark water",
    "a great white shark gliding directly below her",
    "a humpback whale surfacing with one eye above water",
    "a giant manta ray passing overhead like a living ceiling",
    "a blue whale just one eye visible the size of a door",
    "a beluga whale approaching from directly in front",
    "a narwhal with a glowing-tipped horn spiraling upward",
    "a giant sea turtle drifting at eye level in green water",
    "an orca circling her in water that barely contains it",
    "a coelacanth ancient face impossible depth curious",
    "a mantis shrimp tiny devastating staring",
    "a lion mane jellyfish the size of a car overhead",
    "a giant clam slowly opening and closing beside her",
    # Birds
    "a murder of crows dozens perched and landing",
    "a single raven with something stolen and shiny",
    "a barn owl perched on her arm staring straight ahead",
    "a bald eagle riding a thermal directly above her",
    "a secretary bird stepping precisely through neon puddles",
    "a cassowary tall blue-faced clearly unafraid of her",
    "a shoebill stork standing in shallow water judging everything",
    "a harpy eagle descending from a canopy directly overhead",
    "an albatross with a ten-foot wingspan landing beside her",
    "a flock of starlings murmurating into the shape of her outline",
    "a great horned owl whose eyes match her cyan glow",
    "a flamingo flock in black water that reflects neon",
    "a condor on a cliff edge beside her both looking down",
    "a lyrebird performing its tail spread into a perfect mirror of the landscape",
    # Primates
    "a silverback gorilla sitting across from her",
    "a chimpanzee that picked up her dropped lighter and will not give it back",
    "a mandrill with a face that looks like neon war paint",
    "an orangutan that braided something into her hair without asking",
    "a gibbon swinging past close enough to brush her shoulder",
    "a bonobo that keeps offering her fruit she keeps declining",
    # Reptiles
    "a saltwater crocodile motionless in black water",
    "a komodo dragon walking parallel to her on a ruined road",
    "a reticulated python twelve feet long draped across her shoulders",
    "a Galapagos tortoise she apparently sat down to wait beside",
    "a chameleon on her arm cycling through impossible colors",
    "a frilled lizard displaying at something behind her",
    "a black mamba rising to look her in the eye",
    "an anaconda in dark water only its head above the surface",
    "a horned lizard that fits in her palm and refuses to leave",
    "an iguana on a neon rooftop at total ease",
    # Insects & Small
    "a swarm of glowing fireflies forming a constellation",
    "a tarantula the size of a dinner plate on her shoulder and she is fine",
    "a morpho butterfly with wings that glow blue in the dark",
    "a praying mantis on her finger cleaning itself",
    "a hercules beetle she is comparing to her fist",
    "a goliath birdeater spider she is letting walk up her arm",
    "a colony of leafcutter ants carrying pieces of glowing plant",
    "a monarch butterfly migration flowing through and around her",
    "a luna moth with a six-inch wingspan resting on her collarbone",
    # Ungulates
    "a moose with an absurdly massive rack of antlers unfazed by her",
    "a cape buffalo that stopped to look at her and has not moved",
    "a wild horse at full gallop pulling up short beside her",
    "a bison standing in snow breathing visible not moving",
    "a reindeer with frost on its antlers bumping her with its nose",
    "a musk ox with horns low deciding she is probably okay",
    "a pronghorn antelope at full sprint frozen at the exact second it passes",
    # Elephants
    "an African elephant whose trunk reaches toward her face",
    "a baby elephant that will not stop following her",
    "an elephant matriarch standing between her and the horizon",
    # Wild Cards
    "a red fox kit with oversized ears and glowing eyes",
    "a wolverine absolutely refusing to move out of her way",
    "a honey badger staring up at her with total contempt",
    "a capybara that somehow has the vibe of an old friend",
    "a pangolin curled into a perfect sphere in her hands",
    "a platypus that found her in the most unexpected possible setting",
    "an axolotl in water that catches neon light",
    "an aye-aye with its long finger pointing directly at her",
    "a shoal of piranhas forming a single coordinated shape around her",
    "a hermit crab that upgraded to a neon sign for a shell",
    "a cuttlefish whose color patterns sync with her glow",
    "a vampire bat that found her interesting enough to land on",
    "a slow loris with round enormous eyes venomous also very cute",
    "a star-nosed mole surfacing at exactly her feet",
    "a quokka too happy suspiciously happy",
    "a tardigrade she is looking through a microscope at it but it is looking back",
]

# ─────────────────────────────────────────────
# COMPANIONS — TECHNOLOGY & MACHINES (100+)
# ─────────────────────────────────────────────

COMPANIONS_TECH = [
    # Doppelganger / Mirror
    "her own holographic duplicate stepping out of a cracked mirror",
    "a glitching digital clone that is two seconds behind her every move",
    "a pixelated ghost version of herself from an older build",
    "a wireframe skeleton version of herself walking parallel",
    "a neon-outlined silhouette of herself from an alternate timeline",
    "a monochrome version of herself on the other side of a glass wall",
    "a corrupted backup of herself same look wrong eyes",
    "a future-version of herself stepping backward through a portal",
    "a mirror-reversed version of herself who makes every choice opposite",
    "a translucent version of herself from the night this all started",
    # Mecha & Robots
    "a giant bipedal mecha kneeling with its hand extended like a platform",
    "a combat mech with her name graffitied across its chest",
    "a decommissioned war mech whose eyes just powered back on",
    "a rusted giant robot half-buried in a field one arm still reaching",
    "a construction mech abandoned mid-job that turned its head toward her",
    "a spider-legged mech the size of a building walking overhead",
    "a nano-mech swarm the size of a person semi-humanoid",
    "a defunct military mech she has been repairing now sitting up",
    "a child-sized toy robot following two steps behind her",
    "a mech suit she is halfway inside it is assembling around her",
    "a downed mech she is sitting on top of it is not down anymore",
    "a mech built to look like her same proportions different material",
    # Androids & AI Bodies
    "a broken android whose face is almost identical to hers",
    "an android still in its factory crate first eyes open",
    "a decommissioned android that remembered something it was not supposed to",
    "an android learning to mirror her expressions in real time",
    "a chrome humanoid robot whose surface shows her reflection perfectly",
    "a nearly-finished android assembled but not yet activated eyes opening",
    "two androids having an argument she is mediating",
    "an android that was supposed to replace her doing something unexpectedly kind",
    "a military android unit who defected and found her",
    "an android in the exact outfit she was wearing last week",
    # Vehicles & Transport
    "a sentient cyber-motorcycle mid-transformation around her",
    "a self-driving black cab whose interior screens show her face",
    "a hovering skateboard that keeps trying to get her to step on it",
    "a fighter jet with cockpit open engines warm waiting",
    "a subway train that stopped for her specifically doors opening",
    "a vintage car with a chassis that runs on contained lightning",
    "a helicopter drone large enough to carry her hovering at eye level",
    "a cargo truck whose AI keeps finding excuses to drive past her",
    "a submersible with a cracked viewport and one working light inside",
    "a rocket sled on a test track she is about to sit on",
    "a glowing neon tram that runs a route nobody programmed",
    "a space capsule splashed down in front of her hatch unlocking",
    # Drones & Swarms
    "a drone swarm forming a second pair of glowing arms around her",
    "a surveillance drone that started following her for the wrong reasons",
    "a delivery drone that keeps bringing her things she did not order",
    "a nano-drone swarm forming a living halo above her head",
    "a combat drone that switched sides and is now her shadow",
    "a swarm of micro-drones spelling something in the air behind her",
    "a single massive observation drone hovering close lens wide open",
    "a search-and-rescue drone that found exactly what it was looking for",
    "a racing drone frozen mid-loop around her",
    "a drone that has been mapping her face for seventeen minutes",
    # Screens & Projections
    "a massive billboard that reached out pixelated hands toward her",
    "a holographic AI assistant who got too attached",
    "a cracked screen still playing the last moment she looked at it",
    "a floating display that changes content based on her expression",
    "a sentient holoprojector replaying a memory she almost forgot",
    "a city-sized LED display forming one coherent message meant only for her",
    "a VR headset hovering in air already showing the world she is thinking about",
    "a glitching traffic camera that has been tracking her for blocks",
    "a security camera that rotated to face her and did not stop",
    "a cinema screen playing footage of something that has not happened yet",
    # Structures & Infrastructure
    "a server farm she is inside cooling fans moving her hair",
    "a particle accelerator ring she is standing at the center of",
    "a satellite that fell out of orbit and landed nearby still transmitting",
    "a massive antenna array that pivoted to point at her",
    "a supercomputer the size of a room whose indicator lights spell her name",
    "a nuclear reactor cooling tower she is on top of steam around her",
    "a power grid relay station pulsing her exact frequency",
    "a decommissioned space station section she is repurposing",
    "a mainframe so old its interface language is extinct she is reading it",
    "a fusion reactor prototype achieving ignition in the chamber behind her",
    # Weapons & Defense
    "a turret system that turned toward her and then deliberately turned away",
    "a deactivated railgun she is leaning against it is the size of a ship",
    "a bomb disposal robot that found something she dropped and is returning it",
    "a defensive EMP array wrapped in the same cyan she radiates",
    "a directed energy weapon that adjusted its aim to point just past her",
    # Symbiotic / Wearable
    "a Venom-like symbiote forming black leather clothing around her body",
    "a nanosuit assembling itself onto her from a pool of mercury",
    "a smart armor that arrived without being called fitting itself to her",
    "a liquid-metal exoskeleton flowing up her legs just started",
    "a glowing neural interface crown floating down toward her head",
    "a power armor suit cracking open interior lit up waiting",
]

# ─────────────────────────────────────────────
# COMPANIONS — NATURE & ELEMENTS (100+)
# ─────────────────────────────────────────────

COMPANIONS_NATURE = [
    # Trees & Plants
    "an ancient tree whose roots are reaching toward her across the ground",
    "a sequoia so wide she cannot see past it one hand on the bark",
    "a weeping willow whose branches reach down like hands",
    "a dead tree completely covered in bioluminescent moss",
    "a banyan tree whose aerial roots form a room around her",
    "a baobab whose trunk is wider than a house hollow glowing inside",
    "a dragon blood tree with umbrella canopy dripping red resin",
    "a tree struck by lightning that grew back in a spiral of charred neon",
    "a venus flytrap the size of a car gently curious",
    "a pitcher plant large enough to hold water she could bathe in",
    "a rafflesia the size of a dining table strange and alive",
    "a strangler fig slowly completing its century-long spiral",
    "a bamboo grove animated all stalks leaning toward her",
    "a giant sunflower that rotates to track her rather than the sun",
    "a tree that blooms in colors that match her glow on contact",
    "a mangrove root system rising from black water like reaching hands",
    "a cactus forest where each spine glows like a filament",
    "a cherry blossom tree in full bloom even though nothing else is",
    "a tree made entirely of petrified lightning still crackling",
    "a yew tree whose berries glow the exact color of her eyes",
    # Weather & Sky
    "a living storm cloud at eye level releasing controlled lightning",
    "a tornado of cherry blossoms and neon debris she is directing",
    "a hurricane eye wall perfectly still where she stands",
    "a waterspout spiraling up from a glowing ocean directly in front",
    "a lightning storm that is playing favorites with her specifically",
    "an aurora borealis ribbon descending to ground level around her",
    "a weather front the exact line where storm becomes calm",
    "a sandstorm wall a mile high that stopped at her outstretched hand",
    "a blizzard that moves around her like water around stone",
    "a fog bank rolling in and forming shapes she recognizes",
    "a supercell thunderstorm she is standing directly under",
    "a wall cloud with rotation that started when she looked at it",
    "a fire whirl a flaming tornado burning cyan at the base",
    "ball lightning circling her at face height in perfect orbit",
    "a hailstorm frozen mid-fall around her in a perfect sphere",
    "a rainbow that starts and ends at her feet",
    "a moonbow over dark water that intensifies when she steps toward it",
    "a sun pillar of light that follows her across a frozen landscape",
    "a glory circular rainbow halo forming around her shadow",
    "heat lightning illuminating storm clouds in her exact colors",
    # Water & Ocean
    "a wave of liquid neon rearing up like a living thing behind her",
    "a waterfall of liquid starlight she is standing in front of",
    "a frozen waterfall beginning to thaw from her proximity",
    "a geyser erupting in cyan steam directly beside her",
    "a river that reversed direction when she stepped to its edge",
    "a tidal bore a wall of water filling a river channel toward her",
    "a bioluminescent algae bloom glowing the exact shade of her eyes",
    "an ice shelf calving into glowing water behind her",
    "a whirlpool forming in still water she is standing over",
    "an underwater thermal vent lighting water from below her",
    "a lake that reflects a sky that is not actually there",
    "a cenote circular deep impossibly clear pulling light inward",
    "a hot spring that glows and steams in total darkness",
    "a frozen lake cracking in fractal patterns under her feet",
    "rain that falls upward all around her",
    # Earth & Stone
    "a volcanic eruption in the middle distance lava flowing toward her",
    "a lava field with skylights of white-hot rock beneath the surface",
    "a basalt column field she is navigating columns rearranging slowly",
    "a crystal cave with formations taller than she is",
    "a cave of geodes cracking open around her each glowing differently",
    "a stalactite cavern whose formations hum at her resonant frequency",
    "a salt flat that reflects a perfectly inverted sky",
    "a mesa edge with ten thousand feet of canyon below",
    "a glacier flowing visibly carving new terrain around her",
    "a slot canyon whose walls glow in the light that reaches down",
    "a lava tube she is inside walls cooling from orange to black",
    "a volcanic caldera lake acid-green water she is at the edge",
    "sand dunes in a desert at night each grain glowing faintly",
    "a sinkhole opening in the earth revealing a lit cavern below",
    "a fault line actively expressing itself in slow rock movement",
    # Fire & Light
    "a wildfire that forms a perfect ring around her without closing",
    "a controlled burn she is walking through unbothered",
    "a bioluminescent forest every surface glowing its own color",
    "a lava flow she is matching pace with down a hillside",
    "phosphorescent waves breaking at her feet",
    "a coronal mass ejection aurora energy descending to touch her",
    "foxfire pale spontaneous cold-flame lighting the forest floor",
    "will-o-wisps forming an audience in a dark swamp",
    "a burning building she just walked out of still on fire behind her",
    "a controlled burn that shapes itself into a face looking at her",
    # Abstract Nature
    "a migratory event ten thousand birds filling the sky above her",
    "a locust swarm moving around her like water around a stone",
    "a spore cloud from a massive fungal bloom",
    "mycelium network visible through a glass forest floor lit from below",
    "a coral reef rising above water level around her",
    "a volcanic island actively forming at the ocean surface",
    "a meteor crater she is standing at the center of",
    "a double rainbow that perfectly frames her from behind",
    "a magnetic anomaly making compasses spiral and metal objects float",
    "a sinkhole revealing a glowing underground river directly at her feet",
]

# ─────────────────────────────────────────────
# INTERACTIONS — TENDER (100+)
# ─────────────────────────────────────────────

INTERACTIONS_TENDER = [
    "resting her forehead against its",
    "one hand on its face expression unreadable but warm",
    "laughing at something only they both understand",
    "braiding glowing flowers into its fur or feathers or mane",
    "sharing a quiet moment both looking at the same distant point",
    "scratching behind its ear while it leans all the way into her hand",
    "pressing her palm flat against its chest where a heart would be",
    "feeding it something that glows in her open palm",
    "both sitting in the same silence no explanation needed",
    "her head resting against its side eyes closed",
    "letting it smell her wrist and waiting while it decides",
    "crouching to be eye level with it patient",
    "singing something low and quiet while it stills completely",
    "holding its face in both hands while it tries to look away",
    "wiping something off its face like she has done it a hundred times",
    "offering her hand open letting it decide to approach",
    "sitting with her back against it while it sleeps",
    "tracing a scar or marking on it like she is reading braille",
    "falling asleep against it it watching over her",
    "nose to nose breathing the same air both extremely still",
    "her thumb running along its jaw while it makes a sound like trust",
    "wrapping both arms around something enormous and pressing her cheek to it",
    "sitting in its shadow on purpose watching the light change",
    "her hand resting on top of its paw or claw or talon much smaller",
    "making eye contact through glass or water or flame and not looking away",
    "the two of them watching something together that neither can explain",
    "her fingers in its feathers or fur not pulling just there",
    "it lowering its massive head to her level so she can reach",
    "her pressing her lips to its forehead without announcement",
    "both of them turning at the same moment toward the same thing",
    "her sitting cross-legged in front of it both perfectly still",
    "it curled around her while she reads or waits",
    "her drawing something on its surface absently while thinking",
    "both drenched and exhausted in the same way from the same thing",
    "her fixing something broken on it with steady hands",
    "it watching her sleep from a respectful distance",
    "her humming something to it that she has not hummed in years",
    "both looking up at the same thing from the same angle",
    "her lying flat on her back next to it staring at the ceiling",
    "it pressing its weight gently against her side and staying",
    "her hand moving through its smoke or light or water like water",
    "both still in a world that is moving fast around them",
    "her talking to it like it understands every word because it does",
    "it arriving without being called and her not being surprised",
    "her sitting on the highest point of it looking at the horizon",
    "both warm from the same source in the cold",
    "her pressing her ear to it listening for something interior",
    "it choosing her out of everything in the environment",
    "her acknowledging it with one look that says everything",
    "the moment she realized she trusted it and it already knew",
]

# ─────────────────────────────────────────────
# INTERACTIONS — TENSION (100+)
# ─────────────────────────────────────────────

INTERACTIONS_TENSION = [
    "staring it down from two feet away neither one blinking",
    "one hand gripping its horn or snout or claw or collar",
    "mid-negotiation finger raised like she is making her final point",
    "both frozen she made a move it is deciding what that means",
    "her smirking it clearly irritated and trying to hide it",
    "standing between it and something it wants",
    "arm outstretched holding it back like that is enough",
    "circling each other slowly both calculating",
    "eye level with something ten times her size and not yielding an inch",
    "her hand on its jaw tilting its face toward her whether it wants that or not",
    "back to back with it facing opposite threats",
    "mid-argument she said something and it heard all of it",
    "giving it a look that stopped it mid-motion",
    "it coming toward her and her not moving",
    "her finger on its nose and it has gone very still",
    "the exact moment before a choice gets made",
    "her blocking a door or passage it wants through",
    "both of them reaching for the same thing",
    "her matching its posture perfectly deliberate",
    "it growling or crackling or sparking her expression unimpressed",
    "a standoff that has been going for a while neither side ready to move",
    "her saying something final it listening this time",
    "a dare that she accepted and it now realizes she meant",
    "the moment it figured out she is not afraid of it",
    "her holding its gaze until it looks away first",
    "mid-negotiation where she has more leverage than expected",
    "both assessing each other at exactly the same time",
    "it rearing back her stance not changing",
    "her walking toward it while everything else runs the other direction",
    "a line drawn between them nobody yet crossing",
    "both occupying the same small space by choice",
    "her turning her back on it knowing it will not move",
    "the thing that surprised it and did not surprise her",
    "her giving it exactly one warning",
    "it testing her boundary finding it solid",
    "the silence after she said the last true thing",
    "her hand raised flat not defensive just stop",
    "both breathing hard from what just happened",
    "the moment right before it became an understanding",
    "her making something clear that needed to be made clear",
    "both standing their ground in the same storm",
    "it circling her at decreasing distance her tracking it without turning",
    "the exact second the power balance shifted",
    "her meeting something at its own level of intensity",
    "it uncertain for the first time and her watching that happen",
    "the thing between them that has no name but both feel",
    "her saying nothing and that being the answer",
    "both committed now no way to go but forward",
    "the pause that meant something different to each of them",
    "her choosing not to flinch and that changing everything",
]

# ─────────────────────────────────────────────
# INTERACTIONS — PLAY (100+)
# ─────────────────────────────────────────────

INTERACTIONS_PLAY = [
    "both mid-laugh the moment caught between two things that happened",
    "wrestling in the mud or snow or neon water equally matched",
    "riding it backwards just to make a point",
    "playing a game whose rules only they know",
    "hanging off it upside down completely at ease",
    "chasing each other through a neon environment",
    "both covered in the same inexplicable glowing substance",
    "it stealing something her pretending to be upset",
    "her doing something ridiculous it watching with trust",
    "a dare in active progress that she is absolutely going through with",
    "both sprinting toward something neither of them can explain",
    "her using it as a launching pad and it cooperating perfectly",
    "mid-celebration the two of them in the center of a scene they caused",
    "it chasing her and her clearly letting it",
    "her teaching it a trick it keeps getting deliberately wrong",
    "a prank she played on it that it is now replaying on her",
    "the moment after something went wrong and they are both trying not to laugh",
    "both reacting to the same sudden sound in opposite directions",
    "her doing something with total confidence it copying her exactly",
    "a competition that escalated far past where it started",
    "spinning together motion blur her grinning",
    "it knocking her over her lying there grinning at the sky",
    "her swinging from it like it is architecture",
    "both of them drenched in something and not caring at all",
    "a race that is actively happening and it is close",
    "her hiding behind it from something embarrassing",
    "it nudging her off balance just to see what she does",
    "a game of keep-away that she is losing on purpose",
    "her trying to explain the rules of something to it",
    "both ruined both laughing setting unclear",
    "her bouncing something off it watching where it goes",
    "it mimicking her last three moves waiting to see if she notices",
    "the bit they do together that has evolved over time",
    "both mid-sprint for different reasons ending up at the same place",
    "her catching something it threw without looking",
    "the moment it realized she was funny",
    "both in the middle of something that was definitely a bad idea",
    "her pointing at something it caused like it did not just do that",
    "it winning something it should not be able to win she is delighted",
    "the kind of tired that only comes from actual fun",
    "both arriving at the wrong place at the right time",
    "her going first into something it was nervous about",
    "it doing a thing purely to see her reaction",
    "the game that started small and ate the whole day",
    "her landing badly and laughing before she even hits",
    "both of them watching something they set in motion from a safe distance",
    "her explaining why she is right while it clearly disagrees",
    "a high five that evolved into something more elaborate",
    "it surprising her and her immediately wanting to do it again",
    "both in over their heads and completely fine with that",
]

# ─────────────────────────────────────────────
# INTERACTIONS — POWER (100+)
# ─────────────────────────────────────────────

INTERACTIONS_POWER = [
    "it lifting her without effort her directing exactly where",
    "carried bridal-style expression completely unbothered",
    "tentacles or roots or arms wrapping her waist gently and holding",
    "suspended in mid-air held by something enormous and deliberate",
    "perched on its hand or snout or shoulder like that is a throne",
    "it bowing her placing one hand on the back of its head",
    "it surrounding her completely she is the eye of the storm",
    "her palm glowing against its chest both reacting to contact",
    "climbing it like architecture while it stands perfectly still for her",
    "faces inches apart power balanced so precisely neither can move",
    "it in full display expanded glowing enormous all aimed at her",
    "her walking through it as if it is not there it reforming behind her",
    "on its back not holding on arms out completely trusting",
    "it kneeling her walking past without stopping",
    "the moment she redirected it with a gesture",
    "her standing inside it made of weather or light or water unharmed",
    "it at full force she absorbing that and standing",
    "riding it through destruction while her expression stays level",
    "it unfurling its full scale for the first time in her presence",
    "her hand raised and everything stopped",
    "walking into a space it just cleared for her",
    "it converging toward her from every direction and she let it",
    "the moment her touch changed what it was doing",
    "it bending its enormous trajectory just because she stepped into the path",
    "her at the center of something massive revolving around her",
    "it lowered head down waiting for what she decides",
    "her sitting at the edge of it feet dangling no fear",
    "the moment she proved she was the one in charge",
    "it offering something immense and her accepting like it is ordinary",
    "her directing with one finger what took that thing its whole lifetime to learn",
    "it brought to a halt by her standing in its path",
    "her ascending into something massive that opens for her",
    "the kind of scale difference that should be terrifying and is not",
    "it responding to her frequency rather than anything else",
    "her inside something powerful not contained just present",
    "both moving at the same velocity in the same direction",
    "it anchoring her while everything else moves",
    "her holding something back by existing in front of it",
    "the moment everything deferred to her",
    "it taking her weight without comment",
    "her occupying the center of its attention without trying",
    "it catching her from something at the last possible second",
    "her standing on top of the thing that was meant to stop her",
    "it creating a path specifically for her through the impossible",
    "her presence changing the behavior of something enormous",
    "it choosing her as its fixed point",
    "her simply being here meaning it will not go further",
    "the moment she became the reason it stayed",
    "both forces at rest together for now",
    "her walking away from it it not following but watching until she is gone",
]

# ─────────────────────────────────────────────
# CLOTHING (100+)
# ─────────────────────────────────────────────

CLOTHING = [
    # Core leather / cyber
    "black leather jacket open over dark sports bra and high-waist leather pants",
    "full black leather catsuit with a single cyan seam running spine to collar",
    "oversized leather biker jacket over nothing but high-waist leather shorts",
    "sleeveless leather vest with exposed midriff and leather flare pants",
    "double-breasted black leather peacoat belted at the waist",
    "leather corset cinching an oversized white dress shirt tucked into leather pants",
    "cut-off leather jacket with chain-link hem over a leather bodysuit",
    "leather halter crop top with leather wide-leg trousers",
    "leather jacket worn as a dress belted nothing underneath but thigh-highs",
    "leather moto jacket with matching leather racing stripe pants",
    # Cyber / Neon
    "full black latex catsuit with neon-cyan seams that pulse",
    "wet ripped fishnet bodysuit with glowing cyan harness straps",
    "transparent holographic dress that flickers and phases at the edges",
    "neon-veined sheer bodysuit under an open black latex duster",
    "circuit-board patterned bodysuit with glowing trace lines",
    "full-body iridescent black latex with data-stream light effects",
    "cyber-samurai breastplate with glowing cyan accents over black leather",
    "tactical black vest with cyan fiber-optic trim over mesh shirt",
    "neon-stitched tear-away fashion over a matte black base",
    "holographic scale-mail dress that shifts color with movement",
    "segmented carbon-fiber armor panels with neon gaps between",
    "liquid-metal dress that hardens at contact points",
    "bioluminescent bodysuit that glows brighter under pressure",
    "dark chrome-plated shoulder armor over minimal black layers",
    "projection-mapped bodysuit cycling through neon geometric patterns",
    # Goth / Dark Fashion
    "Victorian corset made of circuit boards and dark leather",
    "black lace ballgown with torn skirt and exposed corset bones",
    "shredded black lace catsuit with strategic neon accents",
    "gothic wrap dress in black velvet with deep asymmetric slit",
    "dark empire-waist gown with leather overbust cincher",
    "corseted black taffeta ballgown with asymmetric hemline",
    "dark floral lace bodysuit under sheer black maxi skirt",
    "long-sleeved fishnet dress over matte black undergarments",
    "black satin slip dress with leather harness over it",
    "velvet off-shoulder bodysuit with leather-trimmed skirt",
    # Streetwear
    "ripped oversized band tee knotted at the waist with leather micro shorts",
    "sporty black cropped hoodie with asymmetric leather micro skirt",
    "black bike shorts with matching sports bra and oversized zip-up",
    "cropped cargo jacket over ribbed black top with wide-leg cargos",
    "black athletic set with neon trim jacket tied at the waist",
    "oversized black jersey dress belted into a mini with thigh-highs",
    "baggy black denim jacket over a mesh bodysuit with dark jeans",
    "black track pants with a cinched crop sweatshirt",
    "longline black bomber over a fitted turtleneck and bike shorts",
    "utility vest over a sleeveless turtleneck and leather joggers",
    # Fantasy / Armor
    "dark chainmail bikini top with flowing black silk skirt",
    "full black battle armor with etched runes that glow cyan",
    "fur-lined dark fantasy armor partially open",
    "scale armor in dark iridescent black with glowing lining",
    "pauldrons and breastplate over bare midriff and leather pants",
    "steampunk brass harness over black leather and flowing coat",
    "dark elven armor with root-like organic curves and glowing nodes",
    "black plate armor adapted for her silhouette partly removed",
    "warlord cloak over minimal dark armor command posture",
    "gladiator-inspired leather strips and armor at shoulders and wrists",
    "dark ranger leather form-fitted asymmetric built for movement",
    "tribal-inspired leather and bone armor with glowing elements",
    "void knight armor that absorbs all light except at the seams",
    "frost-rimed dark armor with ice crystal growths at the pauldrons",
    "corrupted paladin armor glowing symbols going wrong in beautiful ways",
    # Coats & Dramatic Outerwear
    "oversized leather trench coat open minimal underneath",
    "fur-lined winter coat open wide dark cropped top underneath",
    "massive black cloak open at the front over form-fitted armor",
    "double-length wool coat in charcoal over a cinched black dress",
    "opera-length leather coat moving like water at every step",
    "floor-length sheer black robe over a structural black bodysuit",
    "long black kimono with glowing thread embroidery falling open",
    "black duster with split back moving like wings",
    "a military greatcoat all buttons open worn over absolutely nothing",
    "floor-length black fur coat open to show everything else",
    # Swimwear / Water
    "black wetsuit unzipped to the waist sleeves tied off",
    "one-piece black swimsuit with glowing seam detail",
    "dark bikini top with high-waist leather shorts dripping wet",
    "full-coverage black diving skin with bioluminescent accents",
    "mermaid-scale bodysuit with no back",
    "sheer black sarong over a structured black swimsuit",
    "sleek racing swimsuit with neon stripe ocean behind her",
    "wet white dress shirt over a black swimsuit clinging to everything",
    "black surfer shorts and sports bra standing at the break",
    "mesh cover-up over dark one-piece standing in surf",
    # Minimal / Body
    "glow-in-the-dark body paint strategic black leather accents only",
    "dark body armor plates on bare skin in structural places",
    "neon geometric body paint over a black high-neck leotard",
    "sheer black bodysuit with full-coverage dark undergarments",
    "wrapped black fabric origami-structured no seams visible",
    "matte black tape structure over her silhouette architectural",
    "dark ceremonial markings painted from neck to waist over black shorts",
    # Specific Aesthetic Mashups
    "silk black kimono falling off one shoulder over leather pants",
    "1920s-inspired black fringe dress with leather belt and boots",
    "dark cocktail dress with structural shoulders and leather detailing",
    "schoolgirl uniform corrupted with cyber-spikes and strategic tears",
    "bride-of-the-machine black lace wedding dress neon veil",
    "post-apocalyptic patchwork black leather functional and beautiful",
    "dark military surplus remixed into high fashion",
    "a black suit jacket with nothing underneath cigarette-ad energy",
    "dark academia blazer over a bodysuit with leather shorts",
    "stage outfit corset micro-skirt thigh-highs like she performs for arenas",
]

# ─────────────────────────────────────────────
# ALL POOLS
# ─────────────────────────────────────────────

ALL_COMPANION_POOLS = [
    COMPANIONS_MYTHICAL,
    COMPANIONS_ANIMALS,
    COMPANIONS_TECH,
    COMPANIONS_NATURE,
]

ALL_INTERACTION_POOLS = [
    INTERACTIONS_TENDER,
    INTERACTIONS_TENSION,
    INTERACTIONS_PLAY,
    INTERACTIONS_POWER,
]

# ─────────────────────────────────────────────
# WEIGHT MEMORY
# Tracks recent usage per item. Each use drops
# an item's weight. Weights decay back toward 1.0
# over time so nothing is permanently suppressed.
# State persists to JSON between runs.
# ─────────────────────────────────────────────

import json
import os
import time

# Where weight state lives — same dir as this file
_WEIGHT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "molty_weights.json")

# How much a single use penalizes an item (multiplied onto current weight)
_USE_PENALTY    = 0.25   # one use drops weight to 25% of current
_MIN_WEIGHT     = 0.05   # never fully excluded
# How many seconds for weight to recover halfway back to 1.0
_HALF_LIFE_SEC  = 60 * 60 * 6  # 6 hours


def _load_weights() -> dict:
    if os.path.exists(_WEIGHT_FILE):
        try:
            with open(_WEIGHT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_weights(weights: dict) -> None:
    try:
        with open(_WEIGHT_FILE, "w") as f:
            json.dump(weights, f, indent=2)
    except Exception:
        pass


def _decayed_weight(entry: dict, now: float) -> float:
    """Exponential recovery toward 1.0 from entry's stored weight."""
    elapsed   = now - entry["ts"]
    ratio     = elapsed / _HALF_LIFE_SEC
    current   = entry["w"] + (1.0 - entry["w"]) * (1 - 2 ** -ratio)
    return max(_MIN_WEIGHT, min(1.0, current))


def _weighted_choice(items: list, weights: dict, now: float) -> str:
    item_weights = []
    for item in items:
        entry = weights.get(item)
        w = _decayed_weight(entry, now) if entry else 1.0
        item_weights.append(w)

    total = sum(item_weights)
    r = random.random() * total
    cumulative = 0.0
    for item, w in zip(items, item_weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def _record_use(key: str, weights: dict, now: float) -> None:
    current = _decayed_weight(weights[key], now) if key in weights else 1.0
    weights[key] = {"w": max(_MIN_WEIGHT, current * _USE_PENALTY), "ts": now}


# ─────────────────────────────────────────────
# BUILDER FUNCTION
# ─────────────────────────────────────────────

def build_interaction_clause(
    companion_chance: float = 0.65,
    force_pool: str = None
) -> dict:
    """
    Returns dict: companion, interaction, clothing, has_companion.

    Uses weight memory so recently chosen items drift to lower
    probability and recover automatically over ~6 hours.
    State persists in molty_weights.json next to this file.

    force_pool: 'mythical' | 'animal' | 'tech' | 'nature' | None
    """
    now     = time.time()
    weights = _load_weights()

    clothing = _weighted_choice(CLOTHING, weights, now)
    _record_use(clothing, weights, now)

    if random.random() > companion_chance:
        _save_weights(weights)
        return {"companion": None, "interaction": None,
                "clothing": clothing, "has_companion": False}

    pool_map = {
        "mythical": COMPANIONS_MYTHICAL,
        "animal":   COMPANIONS_ANIMALS,
        "tech":     COMPANIONS_TECH,
        "nature":   COMPANIONS_NATURE,
    }

    companion_pool = pool_map.get(force_pool) if force_pool else random.choice(ALL_COMPANION_POOLS)
    interaction_pool = random.choice(ALL_INTERACTION_POOLS)

    companion   = _weighted_choice(companion_pool, weights, now)
    interaction = _weighted_choice(interaction_pool, weights, now)

    _record_use(companion,   weights, now)
    _record_use(interaction, weights, now)
    _save_weights(weights)

    return {"companion": companion, "interaction": interaction,
            "clothing": clothing, "has_companion": True}


def inject_into_prompt(base_prompt: str, scene_data: dict) -> str:
    prompt = base_prompt.replace("{clothing}", scene_data["clothing"]) \
             if "{clothing}" in base_prompt \
             else base_prompt + f", {scene_data['clothing']}"

    if scene_data["has_companion"]:
        prompt += f", {scene_data['companion']}, {scene_data['interaction']}"

    return prompt


def show_weight_state(top_n: int = 10) -> None:
    """Debug helper — show most suppressed items and their recovery status."""
    now     = time.time()
    weights = _load_weights()
    if not weights:
        print("No weight history yet.")
        return

    rows = []
    for key, entry in weights.items():
        w = _decayed_weight(entry, now)
        recover_hours = (_HALF_LIFE_SEC * (-1 / 0.693) * (w - 1) / max(0.001, 1 - w))
        rows.append((w, key))

    rows.sort()
    print(f"{'Weight':>6}  Item")
    print("-" * 60)
    for w, key in rows[:top_n]:
        hrs = _HALF_LIFE_SEC * (1 - w) / max(0.001, w) / 3600
        print(f"  {w:.2f}  {key[:55]}  (~{hrs:.1f}h to recover)")


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Pool sizes:")
    print(f"  Mythical:     {len(COMPANIONS_MYTHICAL)}")
    print(f"  Animals:      {len(COMPANIONS_ANIMALS)}")
    print(f"  Tech:         {len(COMPANIONS_TECH)}")
    print(f"  Nature:       {len(COMPANIONS_NATURE)}")
    print(f"  Clothing:     {len(CLOTHING)}")
    print(f"  Interactions: {sum(len(p) for p in ALL_INTERACTION_POOLS)}")
    print()

    print("Generating 5 scenes (weights accumulating):")
    for i in range(5):
        d = build_interaction_clause()
        print(f"--- Scene {i+1} ---")
        print(f"Clothing:    {d['clothing']}")
        if d['has_companion']:
            print(f"Companion:   {d['companion']}")
            print(f"Interaction: {d['interaction']}")
        else:
            print("Solo shot")
        print()

    print("\nCurrent weight suppression (most penalized):")
    show_weight_state()
