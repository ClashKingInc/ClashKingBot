import type { Player } from "./game-common";
import type { RankedCutoffs, RankedHit, RankedMember } from "./ranked";
import { posterArtwork as art, posterRemoteImage, posterTownHall, renderPosterSvg } from "./legend-poster";

import { rankedPosterSvg } from "./ranked-poster-layout";

export async function rankedPoster(input:{player:Player;league:string;season:string;member:RankedMember;members:RankedMember[];attacks:RankedHit[];defenses:RankedHit[];cutoffs?:RankedCutoffs}){
 const {player,league}=input;
 const slug=league.toLowerCase().replace(/\s+/gu,"_");
 const [badge,hall,clan]=await Promise.all([
  posterRemoteImage(`https://assets.clashk.ing/leagues/league-tier/${slug}.png`),
  Promise.resolve(posterTownHall(player.townHallLevel)),
  posterRemoteImage(player.clan?.badgeUrls?.small),
 ]);
 return renderPosterSvg(rankedPosterSvg(input,{...art,badge,hall,clan}));
}
