// Mock 规则生成器（按请求动态生成）。

type Query = Record<string, string | undefined>;

type TextItem = {
  id: number;
  fid: string;
  part: string;
  source_text: string;
  translated_text: string | null;
  status: number;
  edit_count: number;
  updated_at: string;
  created_at: string;
  claim_id: number | null;
  claimed_by: string | null;
  claimed_at: string | null;
  is_claimed: boolean;
};

const statuses = [1, 2, 3];

function hash(input: string): number {
  let value = 0;
  for (let i = 0; i < input.length; i += 1) {
    value = (value << 5) - value + input.charCodeAt(i);
    value |= 0;
  }
  return Math.abs(value);
}

function toIso(date: Date): string {
  return date.toISOString();
}

function createTextItem(index: number, seed: string): TextItem {
  const base = hash(`${seed}-${index}`);
  const status = statuses[base % statuses.length];
  const is_claimed = base % 2 === 0;
  const updatedAt = new Date(Date.now() - (base % 3600) * 1000);
  const createdAt = new Date(updatedAt.getTime() - 3600 * 1000);

  return {
    id: 1000 + index,
    fid: `file_${(base % 26) + 1}`,
    part: `p${(base % 5) + 1}`,
    source_text: `254156718::::::[<u>The Foundry</u>\n\qI am almost impressed. You have stumbled upon the source of some most unusual weapons. I wonder if you will be able to uncover the real secret that lies within my foundry.\q]|||228013362::::::[<u>In A Northern Dale</u>\n\qGood luck to you. The road will be a long one, and dangerous.\q]|||97295054::::::[<u>Bâr Nírnaeth, the Houses of Lamentation</u>\n\qNone come unbidden to the Houses of Lamentation. And yet, here are the Living and the Deathless, uninvited and uninitiated. I have not forgotten the rites of old, Master, for Morloth shall soon drink of their blood. There is flesh to be flensed and there are minds to be broken... and all shall be left naked before the Lidless Eye.\q]|||2847668::::::[<u>The Hideout</u>\n\qThe hunt for Amdir leads to the hideout of the brigand Skunkwood, but to what end is unknown....\q]|||31749887::::::[<u>The Point of Decision</u>\n\qWe always knew that the Company of the Ring would face the difficult decision of what road to take. We simply did not know how soon....\q]|||191399505::::::[<u>Outrun the Wind, Outrun the Waves</u>\n\qRide for Umbar! Ride with haste!\q]|||109262887::::::[<u>Running Towards Nothing</u>\n\qGreat and terrible things lurk in the dark of the forest. If any of the refugees from Byre Tor yet survive, they will need aid.\q]|||191399506::::::[<u>The River Gate</u>\n\qIt is not too late, my friend. Our warning will reach the Kindred with hours to spare.\q]|||162240081::::::[<u>A Flight of Drakes</u>\n\qPembar, the resting place of one of the famed forges of Eregion, has fallen beneath the shadow of the drake-matron Rimlug and her brood. The great Wing-mother and her spawn must be defeated if the forge is to be awakened once more....\q]|||6012248::::::[At the outskirts of a dwarf camp in the Rushock Bog, you hope to put an end to the dwarf Olwir's plan to capture a Stone-troll and give it as a gift to the resurrected Skorgrím in the north.]|||162240082::::::[<u>The Training Hall</u>\n\qMany armouries and forges of the dwarves lie dormant in Khazad-dûm, awaiting the hands of their masters. One such has been claimed by the Orcs of Moria for a training hall. If the forge is to see service again, the Orcs must be driven forth....\q]|||191399508::::::[<u>The Cage and the Captives</u>\n\qI hope they are all right.\q]|||162240083::::::[<u>The Ghost-forge</u>\n\qThe ancient tomb of a great dwarf-smith of Khazad-dûm is now the site of a terrible evil. A Cargûl in the service of the Nine has come to the forge, and with him many fell spirits, and has put the fires of the forge to evil use....\q]|||162240084::::::[<u>Midnight Raid</u>\n\qThe servants of Saruman have laid claim to the ancient forges of Eregion. Savage Dunlendings have raised their encampment around one such forge. The men of Dunland must be routed if the crucibles of the forge are to burn once more....\q]|||191399510::::::[<u>The Uprising Begins</u>\n\qGo, then, and good fortune go with you! Good fortune go with us all!\q]|||162240085::::::[<u>The Mithril Slaves</u>\n\qDwarves are not alone in their search for mithril. Orcs and goblins toil within the barren mines, seeking some small vein of Moria-silver to use against the Free Peoples, or at the least to keep it from them....\q]|||162240086::::::[<u>The Morroval Outcasts</u>\n\qIn the deep places of Moria, an ancient and hidden dwarf-forge has been penetrated by an outcast band of merrevail, seeking the tools which lie there in disuse. To what ends such creatures might put them remains unknown....\q]|||148545291::::::[<u>The Red Sky Darkens</u>\n\qMy story begins at the camp on the edge of Agarnaith. You know the one.\q]|||245831155::::::[<u>The Deeping-coomb</u>\n\qSaruman's foul sorcery has destroyed the Deeping Wall and driven the Rohirrim into the Deeping-coomb. The retreat to the Glittering Caves and the Hornburg must be secured if there is to be any hope.\q]|||162240087::::::[<u>The Siege of Barad Morlas</u>\n\qThe kindred of Elrond Halfelven have driven forth the half-orcs from Barad Morlas, but the ancient ruin is not yet safe. Dunlendings march even now upon the encampment, while the Elves tend to their wounds....\q]|||191399513::::::[<u>The Lesson of the Flames</u>\n\qWe will teach our enemies the danger of harnessing the Hungry Fire!\q]|||33804498::::::[<u>Battle for Hamât, Part 2</u>\n\qMizâdi has tracked Bârshud to the fortress of Dun Shûma in Khûd Zagin. The time has come to meet Bârshud in pitched battle and defeat him for good.\q]|||162240088::::::[<u>The Spider Nest</u>\n\qThe returning dwarves go heedlessly into the dark of Moria. Their scouts, seeking a lost forge, find instead a nest of deadly spiders. The spiders prefer the blood of the living, and so there is still hope for their rescue....\q]|||9528962::::::[<u>The Ox and the Dragon</u>\n\qMeanwhile, Radanir of the Dúnedain brings tidings of Lheu Brenin's betrayal to the Uch-lûth in Enedwaith.\q]|||33804499::::::[<u>Battle for Hamât, Part 3</u>\n\qPush into Dun Shûma and end the threat of Bârshud!\q]|||162240089::::::[<u>The Library of Steel</u>\n\qThe Library of Steel contains many secrets of the smithy, protected by the wards of the dwarves, for which they are well-known. Now the Ghâsh-hai seek to summon lesser fire-spirits to break the wards and ravage the library and the forge within....\q]|||200084883::::::[<u>The Roving Threats of Central Gondor</u>\n\qYou gather to defeat the Hardened enemies of Central Gondor who have banded together to stand off against those who oppose them.\q]|||244696693::::::[<u>The Siege of Hytbold</u>\n\qThe Enemy is marching upon Hytbold, intent upon defeating the Lords of the Eastemnet and claiming eastern Rohan as their own.\q]|||69006789::::::[Pelennor Prototype - Visual Test]|||218103224::::::[<u>Negotiations</u>\n\qYou have earned the respect of the formidable Captain Jajax, and he will now negotiate with you regarding the fate of Lothgobel.\q]|||119659925::::::[TBD…]|||222063922::::::[<u>The Reclamation of Talath Anor</u>\n\qLearning of a group of Haradrim, unwilling to surrender, Elfhelm summons you to join him on a mission to rid Talath Anor of these fleeing foes.\q]|||246990133::::::[<u>A Hunter's Charge</u>\n\qAfter receiving word of a pack of Wargs making their way into the Shire, land of the hobbits, the huntress Gytha Lainey has recruited the best hunters to track and slay the evil Wargs before they can harm any of the Shire-folk....\q]|||141259278::::::[The rot from Adagím is spreading. It threatens to bring blight to Kighân, and our farmland. Worse, it is the trees themselves that are spreading this blight. Cut these evil trees down and burn the blight, that it may not tarnish Kighân.]|||101153202::::::[\qThe Temámir of Jiret-menêsh want to know if any relics of Lâkindar of old remain within the Quelling-house, and would be grateful for anything that can be brought to them.\q]|||85106791::::::[<u>Othrongroth</u>\n\qAn unholy alliance is forged within the depths of Othrongroth, the Great Barrow, a sinister pact which could spell doom for Eriador....\q]|||49157380::::::[<u>Rescue by Moonlight</u>\n\qAvorthal had been moved from the Dourhand encampment to a ship preparing to depart for an unknown port in the North. His rescue is paramount to maintaining peace in Ered Luin....\q]|||131597138::::::[<u>Too Far From the City</u>\n\qOsgiliath is lost, and its defenders flee across the plain. Can they reach the White City before the enemy overtakes them?\q]|||55650352::::::[<u>Fornost</u>\n\qFornost, the last capitol of the fallen North Kingdom. It is here that the Witch-king of Angmar crushed the realm of Arnor, and it is here to which Angmar has returned to conquer Eriador.\q]|||93294581::::::[<u>Rage of the Erui</u>\n\qMaddened by the encroaching Haradrim, the Lone Lady has lashed out, raising the long-emptied armours of Men who fought in the Kin-strife to drown those who taint the waters of the Erui. Fearful of her anger growing beyond control, the Sisters of Lebennin have united to calm their Sister and bring peace to Lebennin once more.\q]|||156549379::::::[<u>Prisoner of the Free Peoples</u>\n\qThe pages of Sara Oakheart's journal uncovered the way into the ruins of Delossad, once called Sithad in brighter days. The search for Narchuil has led here, but to what end? What have these ragged stones seen...?\q]|||41797869::::::[<u>The Forges of Khazad-dûm</u>\n\qAt the height of Durin's reign, the Forges of Khazad-dûm were once famed for producing great crafts of beauty and majesty. Now they have fallen into misuse by the Orcs which now infest the ancient halls of Moria, spewing forth their terrible tools of war....\q\n]|||131597144::::::[<u>What the Steward Saw</u>\n\qThere is much to do, and now I hear the Steward has summoned my friend for an audience? Time-wasting rubbish!\q]|||259963840::::::[Prince Ingór has declared a Zhélruka Clan feast to commemorate their new Mountain-home....]|||207856259::::::[<u>Let's Take the Hornburg!</u>\n\qYou have survived the long night standing before the walls of the Hornburg, and it is time to take your prize at last. The horse-men must fall!\q]|||267670899::::::[<u>Death From Below</u>\n\qBeneath the captured tower of Thangúlhad, the earth stirs as a band of goblins strives to undermine the Malledhrim outpost.\q]|||114061077::::::[<u>Last Stand</u>\n\qWildermore has suffered enough loss and heartbreak to last its people many lifetimes. With the return of Thrymm, the hero of the land, it is time for Núrzum's reign of terror to come to an end.\q]|||266340462::::::[<u>Ekal-nêbi, the Fallen Palace</u>\n\qThe palace of Ekal-nêbi is the crown jewel of Emax Dûl, an opulent home to rulers from the kingdom of Nêshak, Nísaka... and now from Ordâkh. Hidden in the background of palace life, Thothril the Entangler, Thardúth of Damudûr, quietly began working her enchantments upon the minds of its inhabitants. Now with soldiers of Mizâdi's alliance at the palace doorstep, she asserts final control over the palace.\q]|||99182821::::::[<u>The Battle for Aughaire</u>\n\qMordirith, the Steward of Angmar was believed defeated, but such hope was in vain. According to the armies of Angmar, Mordirith has returned and now stretched forth his hand to crush the Trév Gallorg in Aughaire....\q]|||139578261::::::[<u>Viznak Lives</u>\n\qViznak has escaped the Halls of Black Lore with his life, but the merrevail are closing in! We must hurry, before Faeron is overrun!\q]|||191411798::::::[<u>Atop the Island</u>\n\qNow we will end the threat of Balakhâd and Nakási once and for all!\q]|||96010596::::::[<u>Days Long Past</u>\n\qSheltered from the evil that has taken hold of the forest, Barallas wishes to recall the days before Núrzum's coming, when the Ents once met at the Enting Hollow.\q]|||252342540::::::[<u>Assembly Call</u>\n\qThe Avanc-lûth have been swayed by your influence in Dunbog and have called an Assembly. There, they will decide if they are to fight the threat of Isengard or remain secluded from the world.\q]|||59972392::::::[TBD]|||118562232::::::[<u>Mekeb-farak</u>\n\qWhen Moria fell, so too did its lore and legends. Within the halls of Mekeb-farak, the stories told by the Dwarves of Moria rest silent and dust covered, waiting for someone to find them.\q]|||120883230::::::[<u>The Water Wheels: Nalâ-dûm</u>\n\qDeep in the abysses of Moria, the dwarves had once crafted a great waterway to bring water in from the mountains. Something now blocks the great wheels from turning, causing the Iron Garrison concern.\q]|||87130805::::::[<u>The First Blade</u>\n\qYou stand at the steps of Cair Andros where the fearsome Sûhalar, Korpûrta, must face the consequences of his actions for the slaughter of Gilgír and his sons.\q]|||14261331::::::[<u>The Sixteenth Hall</u>\n\qThe dread malady that spreads among the servants of the Enemy in Moria is strong in the Sixteenth Hall. Whatever nameless thing dwells there has entrapped many an Orc to its service, poisoning their minds and controlling their actions.\q]|||70508740::::::[<u>Fil Gashan</u>\n\qFil Ghashan is the stronghold of Talug, right hand of Mazog, Lord of Moria. Here, the Orc-general musters an army to make a futile assault upon Lothlórien. Here, he also breeds Orc-warriors of a most deadly skill....\q]|||227685794::::::[<u>The Lord of Gundabad</u>\n\qI hear fighting just ahead! Let us press on!\q]|||116115701::::::[<u>A Disturbance At the Gate</u>\n\qGárwig, the Reeve of Wildermore, has been summoned by a disturbance at the western gate of Forlaw.\q]|||161004622::::::[<u>Battle of the Ford, Afternoon</u>\n\qWe formed up between Théodred and our foes, fighting for our lives and his. There seemed to be no end to the uruks!\q]|||118880689::::::[As the War of Three Peaks drew near its end, the Dwarves of the Gabil'akkâ suffered a sudden, terrible setback. Before the final effort is made to breach the gates of Gundabad, the dwarves must resist falling to despair and overcome their doubts.]|||138961285::::::[<u>Shield-maiden of Rohan</u>\n\qTo appease the grief of Reeve Fríthild's children, Thane Ordlac has chosen to hold a private -- and unsettlingly cheerful -- funeral for the late Reeve of the Broadacres....\q]|||118880690::::::[By the breath of Hrímil Frost-heart, the gates of Gundabad were sealed shut. If the Dwarves of the Gabil'akkâ intend to enter the sacred mountain, they shall first have to overcome the towering wall of ice that separates them from their prize.]|||90298451::::::[<u>Searching the Depths</u>\n\qAnd so we return to Mâkhda Khorbo, the Temple of Sauron. I had hoped to never see this foul place again. And yet, here we are.\q]|||213821062::::::[<u>Retaking Pelargir</u>\n\qThe Corsair fleet has tarried on Gondor's coast, pillaging on their way. Now Aragorn's host has caught up with them at the port city of Pelargir. Join Elladan and Elrohir in an advance party to clear the path for Aragorn's assault on the unsuspecting Corsair force.\q]|||143407310::::::[<u>The Shattered Crown</u>\n\qAfter the fall of Mordirith at Gador Gúlaran, the dread-realm of Angmar was undone yet again. In the wake of its downfall, the folk of that realm and what remained of their Dourhand and Hill-men allies fled beyond Bálach Iaran into Câr Bronach. However, bereft of the wisdom of their masters, the Iron Crown fell into disarray and sought desperately for a means to restore their kingdom of old.\q]|||139371596::::::[<u>Caverns of Thrumfall</u>\n\qDeep within the recesses of the Stormwall lie ancient passages and twisted tunnels, concealing the whereabouts of Etterfang Foulmaw and her restless horde. Only the dwarf Drengur has seen the venomous beast and lived to tell the tale.\q]|||123139937::::::[<u>Siege Escalated</u>\n\qThe White Hand is pressing its assault upon Brockbridge, and the few defending it will be hard-pressed to survive.\q]|||203301566::::::[<u>Doom of Caras Gelebren</u>\n\qDetermined to possess the Great Rings of Power, Sauron made war upon the Elves and led his vast armies to Eregion to lay waste to Caras Gelebren....\q]|||131609430::::::[<u>Sons of Blackroot</u>\n\qMy brother and I have sworn a solemn vow to bring down the mighty Mûmakil that have come to Gondor!\q]|||109143537::::::[<u>Among Enemies</u>\n\qAzagath slew my captors in Jirush, but I felt no gratitude to him. I fled from him, seeking somewhere to hide.\q]|||131609432::::::[<u>Gothmog Appears</u>\n\qOur enemies have brought a great ram to the city. We must damage or destroy it!\q]|||98273444::::::[<u>An Audience with the Cuan-lûth</u>\n\qThough Cariad would like for you to help him approach the Rangers, discussing such matters with the leader of his people may be another problem.\q]|||155897223::::::[<u>Munfaeril's Warning</u>\n\qMadin's grandfather was a good man, giving succour to the People of the Boar when the Draig-lûth nearly destroyed them. Madin and his son Nevid, however, have fallen to evil ways, and I cannot, as a servant of the Huntsman, allow this travesty to continue....\q]|||66321475::::::[<u>Bonds of Oak and Iron</u>\n\qAs the Battle of Azanulbizar continued on the slopes of Zirakzigil and Bundushâthur, King Thráin and his vanguard prepared to assault the gates of Khazad-dûm. Yet, unbeknownst to the Dwarves of the Haban'akkâ, there was unrest at Amdân.\q]|||98273447::::::[<u>At A Cross-roads</u>\n\qThe Cuan-lûth do not bow easily to those with power, and the Rangers of Tornhad are no exception.\q]|||130897527::::::[<u>Memories of Máttugard</u>\n\qFor but a brief moment during the Sixth War of the Dwarves and Orcs, the Haban'akkâ of Thráin gained entry to Mattugard. But beyond the noble gate of Mount Gundabad, Komog, son of Azog, laid in wait to slay all that sought to reclaim even the smallest foothold within his father's realm.\q]|||78722579::::::[<u>Flowers for Eshtali</u>\n\qEshtali lies in the tombs of Esh-kimâkhi. In the fight to liberate Kûr Anzar, there was scarcely enough time to think, let alone mourn the dead. Now that the immediate threat is over, we mourn our fallen and remind ourselves why they still take such firm residence in our hearts.\q]|||158388164::::::[\qPeople are being held prisoner by the Ordâkhai at Kôth Rau, and survivors have said they are sure to be tortured. Someone should enter the camp and rescue the empire's captives.\q]|||15591795::::::[Reports have come in from our scouts to the west that the Huorns are growing more aggressive and threaten what remains in Laivárth. We can not send aid ourselves, but you should be able to put a stop to them.]|||202966292::::::[<u>Wrath of the Reeve</u>\n\qI have taken to the battlefield, hoping to inspire and reassure my people. We fight together, and I wish to witness firsthand your ability in combat.\q]|||144652035::::::[<u>Dark Delvings</u>\n\qIn the deepest delvings of Moria dwell nameless things which shun the light and feed on the darkness. The Elves of Lórien strive to constrain the vile creatures, but led by the evil Gurvand, they may be too strong to hold back forever....\q]|||54958401::::::[Upon the High Pass, a terrible frost drake guards the mountain path....]|||54958402::::::[Upon the High Pass, the Frost-horde has blocked the mountain path....]|||118696996::::::[Rumours tell of a mighty beast unlike any other. Deep in the Shield Isles it lies, who preying on Corsairs and freebooters alike. Venture forth and try to find and tame the mighty beast.]|||192939781::::::[<u>The Last Refuge</u>\n\qSkorgrím's Dourhands have taken refuge from the wrath of Durin's Folk within an ancient dwarf-hold high in the passes of the Misty Mountains. There, they plot their return, unless an end can be put to their scheming once and for all....\q]|||244225221::::::[<u>The Story of a Strange Stone</u>\n\qThere is a story behind the stone fragment you uncovered in Dunfast...\q]|||13933733::::::[<u>Mossward, The Border Village</u>\n\qSpeak, then, of how you came to this place of safety: Rivendell, the Last Homely House East of the Sea. But speak swiftly, before the shadows deepen. From where did your road lead?\q]|||93928484::::::[<u>Taking a Rest</u>\n\qCome, join me by the fire and I will tell you why I am travelling.\q]|||243242323::::::[In the ruins of Sedgemead a new menace arises. Drive the Earth-kin from the ruins.]|||65142625::::::[Despite the failure of the Iron Garrison, the dwarves will not allow the Orcs of Khazad-dûm to spill forth into Azanulbizar, the Dimrill Dale.]|||216223236::::::[<u>A Burglar's Errand</u>\n\qMedhrod, a legendary sword once wielded by a great hero who helped keep the Great East Road clear of threats, has been stolen by the half-orcs of Naerost, leading Palma Brownlock, a hobbit-burglar of no small reputation, to gather allies to recover it....\q]|||65142626::::::[Despite the failure of the Iron Garrison, the dwarves will not allow the Orcs of Khazad-dûm to spill forth into Azanulbizar, the Dimrill Dale.]|||65142627::::::[Despite the failure of the Iron Garrison, the dwarves will not allow the Orcs of Khazad-dûm to spill forth into Azanulbizar, the Dimrill Dale.]|||129755420::::::[Just an ordinary night in a quiet hobbit township. What could possibly go wrong?]|||175415965::::::[<u>Signs and Portents</u>\n\qThe dreaming mind sees much, and much is seen of it...\q]|||65142628::::::[Despite the failure of the Iron Garrison, the dwarves will not allow the Orcs of Khazad-dûm to spill forth into Azanulbizar, the Dimrill Dale.]|||65142629::::::[Despite the failure of the Iron Garrison, the dwarves will not allow the Orcs of Khazad-dûm to spill forth into Azanulbizar, the Dimrill Dale.]|||14987070::::::[<u>A House Forged Anew</u>\n\qAfter seventy-eight years in the dungeons of Barad-dûr, King Váskmun Greytooth of the Stout-axes has returned to lead his folk. However, if there is to remain any hope of forging a new Dwarf-kingdom within Mordor, the Stout-axes must break free of their servitude and challenge the Mistress of Lûghash, Zôreth.\q]|||131621714::::::[<u>Death Comes for All</u>\n\qThe Rohirrim have taken the field, and the armies of Mordor cannot stand against us!\q]|||31521873::::::[Within the old halls of Kallamdâm, in Gundabad, cold-drakes of the Frost-horde erect a fortress of ice....]|||103768232::::::[<u>Battle For Maurûsh</u>\n\qThe time has come to fight with Galâmka and the refugees to reclaim the stronghold of Maurûsh from the Orcs.\q]|||14105218::::::[<u>To Avert a War</u>\n\qThe Ranger Langlas prepares to mount an effort to rescue the Elf-prince Avorthal from the clutches of the treacherous Dourhands....\q]|||189015844::::::[The post is late from the Shire and the news is that something has the post-carrier spooked and unwilling to make the crossing. You have been sent to investigate.]|||31521874::::::[Rumours of permafrost within a frigid dwarf-catacomb begin to circulate....]|||131621716::::::[<u>The Foe Resurgent</u>\n\qThe Witch-king of Angmar is slain, but the forces of the Enemy remain unbroken. Instead of fleeing at the sight of their Master's fate, their resolve is strengthened as countless new foes pour forth from Osgiliath. What other commander could lead such an army against Gondor?\q]|||240036421::::::[<u>Sant Lhoer, the Poison Gardens</u>\n\qKnown as the poison gardens of Carn Dûm, Sant Lhoer is a dank place teeming with deadly plants, trees, and flowers, the likes of which have scarcely or never before been seen in Middle-earth. Above the foetid, beryl-green waters which flow through Sant Lhoer rise immense, pellucid structures, greatest among them Bâr Heledh, the Glass House. It is here that the sorceress Oganuin plies her craft, experimenting upon creatures, plants, and all those who stray too near the ever-grasping tendrils of her creations. To what end, and for what purpose? One can only assume the darkest of designs....\q]|||131621719::::::[<u>A Final Vengeance</u>\n\qWe have to find Golodir before it is too late!\q]|||131621720::::::[<u>On a Field of Red</u>\n\qFight onward! The battle is not yet ended!\q]|||48577221::::::[<u>The Sickle, the Lotus, and the Lion</u>\n\qYou have brought the leaders of Ambarûl, Khûd Zagin, and Imhûlar together in Iridír. Mizâdi has much to do before Girhâzi and Amalíbi trust her or her leadership.\q]|||59580519::::::[<u>Lords of the Eastemnet</u>\n\qSkeptical of the King's state of mind, the Lords of the Eastemnet have gathered to decide how to defend their lands.\q]|||130174932::::::[<u>Attack at Dawn</u>\n\qIn the late evening hours, a small group of refugees sought refuge in the hidden Ranger-camp of Esteldín. These refugees were followed by a small group of goblin-scouts that quickly fled to Dol Dínen to bring word to their chief, Graug. Siniath the Ranger has asked you to seek out Graug and defeat him before he can spread word of Esteldín's location. As you arrive near Dol Dínen, the first rays of the false dawn can be seen overhead.\q]|||52643566::::::[<u>Tûl Zakana, the Well of Forgetting</u>\n\qDeep in the war-torn lands of Imhûlar, locals warn you of an Ordâkhai encampment, a trading post of sorts. It is known as Tûl Zakana, the Well of Forgetting, whose waters will make you forget your troubles, and, if you drink enough, even who you are. But unless you are trading for this water, it's best to stay quite clear of the Well, for many have vanished near it, never to be seen again. You are now tasked by the families of the vanished with investigating the Well and its secrets.\q]|||34244012::::::[<u>Hildith's Council</u>\n\qHildith, the headstrong wife of Grimbold, now leads Grimslade in her husband's absence.\q]|||221693530::::::[<u>Ransacking Gathbúrz</u>]|||`,
    translated_text: status === 3 ? `78110146::::::[匕首[E]]|||141983240::::::[武器光环[e]]|||9224878::::::[标枪[E]]|||5925762::::::[长矛[E]]|||216547474::::::[单手锤[v]]|||94305316::::::[盾牌[E]]|||243436740::::::[长戟[E]]|||57451442::::::[双手棍棒[E]]|||22146::::::[符文石[E]]|||195175125::::::[项链[E]]|||123899485::::::[长柄武器[E]]|||98231988::::::[单手剑[v]]|||128273636::::::[守望者盾[e]]|||115009204::::::[双手剑[E]]|||32111027::::::[战斗护拳[ps]]|||157982151::::::[弩[E]]|||216547490::::::[双手锤[E]]|||175544643::::::[誓缚武备[ps]]|||193564679::::::[耳环[v]]|||131727580::::::[工匠工具[E]]|||111398483::::::[外观[E]]|||56440725::::::[单手钉锤[v]]|||3524837::::::[单手斧[v]]|||208408648::::::[双手法器[E]]|||208408696::::::[单手法器[v]]|||74210020::::::[战马物品[e]]|||114993142::::::[法杖[E]]|||57489301::::::[双手钉锤[E]]|||4863355::::::[斗篷[e]]|||4860067::::::[职业物品[e]]|||232552930::::::[重甲[E]]|||76069157::::::[挂饰[E]]|||194985972::::::[乐器[e]]|||364615::::::[戒指[E]]|||18791::::::[弓[E]]|||248530164::::::[重盾[e]]|||260947378::::::[轻甲[E]]|||3590373::::::[双手斧[E]]|||142198356::::::[臂环[v]]|||206260578::::::[中甲[E]]|||56402866::::::[单手棍棒[v]]|||95393502::::::[投掷武器[E]]` : null,
    status,
    edit_count: status === 3 ? 2 : 0,
    updated_at: toIso(updatedAt),
    created_at: toIso(createdAt),
    claim_id: is_claimed ? 2000 + index : null,
    claimed_by: is_claimed ? "tester" : null,
    claimed_at: is_claimed ? toIso(new Date(updatedAt.getTime() - 300 * 1000)) : null,
    is_claimed,
  };
}

function filterByDateRange(items: TextItem[], from?: string, to?: string): TextItem[] {
  let result = items;
  if (from) {
    const fromTs = new Date(from).getTime();
    if (!Number.isNaN(fromTs)) {
      result = result.filter((item) => new Date(item.updated_at).getTime() >= fromTs);
    }
  }
  if (to) {
    const toTs = new Date(to).getTime();
    if (!Number.isNaN(toTs)) {
      result = result.filter((item) => new Date(item.updated_at).getTime() <= toTs);
    }
  }
  return result;
}

export function generateTexts(query: Query): TextItem[] {
  const total = 200;
  let items = Array.from({ length: total }, (_, i) => createTextItem(i + 1, "texts"));

  if (query.fid) items = items.filter((item) => item.fid.includes(query.fid!));
  if (query.status) {
    const statusValue = Number(query.status);
    if (!Number.isNaN(statusValue)) {
      items = items.filter((item) => item.status === statusValue);
    }
  }
  if (query.source_keyword) {
    items = items.filter((item) => item.source_text.includes(query.source_keyword!));
  }
  if (query.translated_keyword) {
    items = items.filter((item) => (item.translated_text || "").includes(query.translated_keyword!));
  }
  if (query.claimer) items = items.filter((item) => (item.claimed_by || "").includes(query.claimer!));
  if (query.claimed === "true") items = items.filter((item) => item.is_claimed);
  if (query.claimed === "false") items = items.filter((item) => !item.is_claimed);

  items = filterByDateRange(items, query.updated_from, query.updated_to);

  const maxLength = 5000;
  return items.map((item) => ({
    ...item,
    source_text:
      item.source_text.length > maxLength ? `${item.source_text.slice(0, maxLength)}...` : item.source_text,
    translated_text:
      item.translated_text && item.translated_text.length > maxLength
        ? `${item.translated_text.slice(0, maxLength)}...`
        : item.translated_text,
  }));
}

export function generateTextDetail(textId: number): TextItem {
  const index = Math.max(1, textId - 1000);
  return createTextItem(index, "detail");
}

export function generateDictionary(query: Query) {
  const total = 20;
  let items = Array.from({ length: total }, (_, i) => ({
    id: 3000 + i,
    term_key: `term_${i}`,
    term_value: `译文_${i}`,
    category: i % 2 === 0 ? "race" : "place",
    is_active: i % 3 !== 0,
    created_at: toIso(new Date(Date.now() - i * 60000)),
    updated_at: toIso(new Date(Date.now() - i * 30000)),
  }));

  if (query.keyword) {
    items = items.filter((item) =>
      item.term_key.includes(query.keyword!) || item.term_value.includes(query.keyword!)
    );
  }
  if (query.term_key) {
    items = items.filter((item) => item.term_key.includes(query.term_key!));
  }
  if (query.term_value) {
    items = items.filter((item) => item.term_value.includes(query.term_value!));
  }
  if (query.category) {
    items = items.filter((item) => item.category === query.category);
  }
  if (query.is_active) {
    const isActive = query.is_active === "true";
    items = items.filter((item) => item.is_active === isActive);
  }

  return items;
}

export function generateChanges(textId?: number) {
  const baseId = textId ? textId : 1001;
  return Array.from({ length: 5 }, (_, i) => ({
    id: 5000 + i,
    text_id: baseId,
    user_id: 1,
    before_text: `Before ${i}`,
    after_text: `After ${i}`,
    reason: i % 2 === 0 ? "修正" : "补充",
    changed_at: toIso(new Date(Date.now() - i * 120000)),
  }));
}
