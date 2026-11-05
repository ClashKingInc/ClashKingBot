// Archer/Goblin: user-supplied fan-kit templates. Giant panels: Supercell
// Traumatized_1 (145532) and Traumatized_2 (145531). Grandma: Sure_grandma
// (148956), lettering removed. Comparison: newly generated Clash adaptation.
export const memeTemplates = {
 pepe: {name:"Pepe sign",description:"One caption on Pepe’s sign",labels:["Sign text"]},
 archer: {name:"Archer approval",description:"Reject one thing, approve another",labels:["No thanks", "Yes please"]},
 goblin: {name:"Goblin plan",description:"Four steps, one bad realization",labels:["Step 1", "Step 2", "Step 3", "The realization"]},
 giant: {name:"Giant reaction",description:"Calm on the left, traumatized on the right",labels:["Calm caption", "Traumatized caption"]},
 comparison: {name:"Same picture",description:"Two things that are really the same",labels:["Left picture", "Right picture"]},
 distracted: {name:"Distracted Barbarian",description:"Barbarian, Archer and a distracting Valkyrie",labels:["Valkyrie (distraction)", "Barbarian (distracted)", "Archer (girlfriend)"]},
 forbetter: {name:"For the better, right?",description:"A confident Barbarian and a suspicious Archer",labels:["Barbarian’s statement", "Archer’s hopeful reply", "Archer’s worried reply"]},
 dragons: {name:"Three Dragons",description:"Two serious Dragons and one goofy Dragon",labels:["Left Dragon", "Middle Dragon", "Goofy Dragon"]},
 trade: {name:"Trade offer",description:"Goblin dealmaking in the purple room",labels:["I receive", "You receive"]},
 awkward: {name:"Awkward Goblin",description:"The awkward puppet glance",labels:["Caption"]},
 grab: {name:"Held back",description:"A Barbarian reaches while the Warden holds him back",labels:["Barbarian", "What he wants", "Grand Warden"]},
 presentation: {name:"Archer presentation",description:"Make your point on the big screen",labels:["Presentation text"]},
 terminator: {name:"P.E.K.K.A & Larry",description:"P.E.K.K.A finds a terrified Larry",labels:["P.E.K.K.A", "Larry"]},
 window: {name:"Grand Warden at the window",description:"Watching the Archer and Barbarian have fun",labels:["Grand Warden", "Archer & Barbarian"]},
 kingphoto: {name:"King’s photo",description:"The Barbarian King misses something",labels:["Photo caption"]},
 skeptical: {name:"Skeptical Bowler",description:"The skeptical kid, with a Bowler",labels:["Top caption", "Bottom caption"]},
 always: {name:"Always has been",description:"Two Archer Queens and one realization",labels:["First Queen’s realization", "Second Queen’s reply"]},
 buttons: {name:"Two buttons",description:"A Barbarian faces a difficult choice",labels:["Left button", "Right button"]},
 grandma: {name:"Sure, grandma",description:"A bold claim and a gentle reality check",labels:["The claim", "The reply"]},
} as const;
export type MemeTemplate = keyof typeof memeTemplates;
export function isMemeTemplate(value:string):value is MemeTemplate{return Object.hasOwn(memeTemplates,value);}
