package twitch;

import ThMod.characters.Marisa;
import basemod.BaseMod;
import basemod.CustomCharacterSelectScreen;
import basemod.ReflectionHacks;
import basemod.interfaces.PostBattleSubscriber;
import basemod.interfaces.PostRenderSubscriber;
import basemod.interfaces.PostUpdateSubscriber;
import basemod.interfaces.StartGameSubscriber;
import battleaimod.BattleAiMod;
import battleaimod.networking.AiClient;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.evacipated.cardcrawl.modthespire.lib.SpireConfig;
import com.gikk.twirk.Twirk;
import com.gikk.twirk.types.users.TwitchUser;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.megacrit.cardcrawl.cards.AbstractCard;
import com.megacrit.cardcrawl.cards.DescriptionLine;
import com.megacrit.cardcrawl.characters.Defect;
import com.megacrit.cardcrawl.characters.Ironclad;
import com.megacrit.cardcrawl.characters.TheSilent;
import com.megacrit.cardcrawl.characters.Watcher;
import com.megacrit.cardcrawl.core.CardCrawlGame;
import com.megacrit.cardcrawl.core.Settings;
import com.megacrit.cardcrawl.dungeons.AbstractDungeon;
import com.megacrit.cardcrawl.helpers.*;
import com.megacrit.cardcrawl.relics.*;
import com.megacrit.cardcrawl.rooms.AbstractRoom;
import com.megacrit.cardcrawl.rooms.ShopRoom;
import com.megacrit.cardcrawl.screens.GameOverScreen;
import com.megacrit.cardcrawl.screens.charSelect.CharacterOption;
import com.megacrit.cardcrawl.ui.buttons.ReturnToMenuButton;
import com.megacrit.cardcrawl.unlock.UnlockTracker;
import communicationmod.CommunicationMod;
import hermit.HermitMod;
import hermit.characters.hermit;
import ludicrousspeed.LudicrousSpeedMod;
import ludicrousspeed.simulator.commands.Command;
import savestate.SaveState;
import theVacant.characters.TheVacant;

import java.io.FileWriter;
import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

public class TwitchController implements PostUpdateSubscriber, PostRenderSubscriber, PostBattleSubscriber, StartGameSubscriber {
    private static final Texture HEART_IMAGE = new Texture("heart.png");

    private static final long DECK_DISPLAY_TIMEOUT = 60_000;
    private static final long RELIC_DISPLAY_TIMEOUT = 60_000;
    private static final long BOSS_DISPLAY_TIMEOUT = 30_000;

    private static final long NO_VOTE_TIME_MILLIS = 1_000;
    private static final long RECALL_VOTE_TIME_MILLIS = 2_500;
    private static final long FAST_VOTE_TIME_MILLIS = 3_000;
    private static final long NORMAL_VOTE_TIME_MILLIS = 20_000;

    private static int startingHP = 0;
    public static int runId = 0;

    private static Queue<Integer> recallQueue;

    public enum VoteType {
        // THe first vote in each dungeon
        CHARACTER("character", 25_000),
        MAP_LONG("map_long", 30_000),
        MAP_SHORT("map_short", 15_000),
        CARD_SELECT_LONG("card_select_long", 30_000),
        CARD_SELECT_SHORT("card_select_short", 20_000),
        GAME_OVER("game_over", 15_000),
        OTHER("other", 25_000),
        REST("rest", 1_000),
        SKIP("skip", 1_000);

        String optionName;
        int defaultTime;

        VoteType(String optionName, int defaultTime) {
            this.optionName = optionName;
            this.defaultTime = defaultTime;
        }
    }

    /**
     * Used to count user votes during
     */
    private HashMap<String, String> voteByUsernameMap = null;

    /**
     * Tallies the votes by user for a given run. Increments at the end of each vote and gets
     * reset when the character vote starts.
     */
    private HashMap<String, Integer> voteFrequencies = new HashMap<>();

    private VoteType currentVote = null;
    private String stateString = "";

    private String screenType = null;
    public static VoteController voteController;

    public static HashMap<String, Integer> optionsMap;

    private boolean inVote = false;
    private long voteEndTimeMillis;

    ArrayList<Choice> choices;
    ArrayList<Choice> viableChoices;
    private HashMap<String, Choice> choicesMap;

    public static Twirk twirk;

    private boolean shouldStartClientOnUpdate = false;
    private boolean inBattle = false;
    private boolean fastMode = true;
    int consecutiveNoVotes = 0;
    boolean skipAfterCard = true;

    public static long lastDeckDisplayTimestamp = 0L;
    public static long lastRelicDisplayTimestamp = 0L;
    public static long lastBossDisplayTimestamp = 0L;
    public static long pollBetaArtTimestamp = 0L;

    private int previousLevel = -1;
    private int votePerFloorIndex = 0;

    private final HashMap<String, String> cardsToDescriptionMap;
    private final HashMap<String, String> cardNamesToIdMap;

    private final HashMap<String, String> keywordDescriptionMap;
    private final HashMap<String, String> relicDescriptionMap;

    public HashMap<String, Texture> characterPortrats;
    public HashMap<String, CharacterOption> characterOptions;

    public TwitchApiController apiController;

    HashMap<String, Long> betaExpirationsMap;
    SpireConfig betaArtConfig;

    public TwitchController(Twirk twirk) {
        TwitchController.twirk = twirk;
        try {
            apiController = new TwitchApiController();
        } catch (IOException e) {
            e.printStackTrace();
        }

        betaExpirationsMap = new HashMap<>();
        new Thread(() -> {
            try {
                betaArtConfig = new SpireConfig("CommModExtension", "beta_redemptions");

                JsonObject betaMapJson = new JsonParser()
                        .parse(betaArtConfig.getString("beta_timestamps")).getAsJsonObject();

                long now = System.currentTimeMillis();
                for (Map.Entry<String, JsonElement> entry : betaMapJson.entrySet()) {
                    String key = entry.getKey();
                    long expiration = betaMapJson.get(key).getAsLong();
                    if (expiration > now) {
                        betaExpirationsMap.put(key, expiration);
                        UnlockTracker.betaCardPref.putBoolean(key, true);
                    }
                }
                saveBetaConfig();

            } catch (IOException e) {
                e.printStackTrace();
            }
        }).start();

        pollBetaArtTimestamp = System.currentTimeMillis() + 10_000;

        characterPortrats = new HashMap<>();


        characterPortrats.put("ironclad", ImageMaster
                .loadImage("images/ui/charSelect/ironcladPortrait.jpg"));
        characterPortrats
                .put("silent", ImageMaster.loadImage("images/ui/charSelect/silentPortrait.jpg"));
        characterPortrats
                .put("defect", ImageMaster.loadImage("images/ui/charSelect/defectPortrait.jpg"));
        characterPortrats
                .put("watcher", ImageMaster.loadImage("images/ui/charSelect/watcherPortrait.jpg"));

        if (BaseMod.hasModID("MarisaState:")) {
            characterPortrats
                    .put("marisa", ImageMaster.loadImage("img/charSelect/marisaPortrait.jpg"));
        }

        if (BaseMod.hasModID("HermitState:")) {
            characterPortrats.put("hermit", ImageMaster
                    .loadImage("hermitResources/images/charSelect/hermitSelect.png"));
        }

        if (BaseMod.hasModID("VacantState:")) {
            characterPortrats.put("vacant", ImageMaster
                    .loadImage("theVacantResources/images/charSelect/VacantPortraitBG.png"));
        }

        optionsMap = new HashMap<>();
        optionsMap.put("asc", 0);
        optionsMap.put("lives", 0);
        optionsMap.put("recall", 0);
        optionsMap.put("turns", 10_000);
        optionsMap.put("verbose", 1);

        for (VoteType voteType : VoteType.values()) {
            optionsMap.put(voteType.optionName, voteType.defaultTime);
        }

        cardNamesToIdMap = new HashMap<>();
        cardsToDescriptionMap = new HashMap<>();
        CardLibrary.cards.values().stream()
                         .forEach(card -> {
                             String name = card.name.toLowerCase().replace(" ", "");
                             String description = card.description
                                     .stream()
                                     .map(line -> replaceStringSegmentsForCard(line, card))
                                     .collect(Collectors
                                             .joining(" "));

                             String descriptionResult = String
                                     .format("%s: %s", card.name, description);
                             cardsToDescriptionMap.put(name, descriptionResult);
                             cardNamesToIdMap.put(name, card.cardID);

                             try {
                                 card.upgrade();
                                 String upgradedName = name + "+";
                                 String upgradedDescription = card.description
                                         .stream()
                                         .map(line -> replaceStringSegmentsForCard(line, card))
                                         .collect(Collectors
                                                 .joining(" "));
                                 String upgradedDescriptionResult = String
                                         .format("%s: %s", card.name, upgradedDescription);
                                 cardsToDescriptionMap.put(upgradedName, upgradedDescriptionResult);
                             } catch (NullPointerException e) {
                                 // upgrading sometimes nulls out, hopefully just for curses.
                             }
                         });

        keywordDescriptionMap = new HashMap<>();
        GameDictionary.keywords.entrySet().forEach(entry -> {
            String key = entry.getKey();

            key = key.replace("thevacant:", "");

            if (BaseMod.hasModID("HermitState:")) {
                key = key.replace(HermitMod.getModID() + ":", "");
            }

            key = key.toLowerCase().replace(" ", "");

            String description = entry.getValue();

            description = description.replace("#y", "");
            description = description.replace("#b", "");
            description = description.replace("NL", "");

            keywordDescriptionMap.put(key, key + " : " + description);
        });

        relicDescriptionMap = new HashMap<>();
        getAllRelics().forEach(relic -> {
            String key = relic.name;

            key = key.replace("thevacant:", "");

            if (BaseMod.hasModID("HermitState:")) {
                key = key.replace(HermitMod.getModID() + ":", "");
            }

            key = key.toLowerCase().replace(" ", "");

            String description = relic.description;

            description = description.replace("#y", "");
            description = description.replace("#b", "");
            description = description.replace("NL", "");

            description = description.replace("thevacant:", "");

            if (BaseMod.hasModID("HermitState:")) {
                description = description.replace(HermitMod.getModID() + ":", "");
            }

            relicDescriptionMap.put(key, relic.name + " : " + description);
        });
    }

    public void populateCharacterOptions() {
        characterOptions = new HashMap<>();
        ArrayList<CharacterOption> options = ReflectionHacks
                .getPrivate(CardCrawlGame.mainMenuScreen.charSelectScreen, CustomCharacterSelectScreen.class, "allOptions");
        CardCrawlGame.mainMenuScreen.charSelectScreen.options = options;

        for (CharacterOption option : options) {
            if (option.c instanceof Ironclad) {
                characterOptions.put("ironclad", option);
            }

            if (option.c instanceof TheSilent) {
                characterOptions.put("silent", option);
            }

            if (option.c instanceof Defect) {
                characterOptions.put("defect", option);
            }

            if (option.c instanceof Watcher) {
                characterOptions.put("watcher", option);
            }

            if (BaseMod.hasModID("MarisaState:")) {
                if (option.c instanceof Marisa) {
                    characterOptions.put("marisa", option);
                }
            }

            if (BaseMod.hasModID("HermitState:")) {
                if (option.c instanceof hermit) {
                    characterOptions.put("hermit", option);
                }
            }

            if (BaseMod.hasModID("VacantState:")) {
                if (option.c instanceof TheVacant) {
                    characterOptions.put("vacant", option);
                }
            }
        }
    }

    @Override
    public void receivePostUpdate() {
        if (shouldStartClientOnUpdate) {
            shouldStartClientOnUpdate = false;
            inBattle = true;
            startAiClient();
        }

        if (pollBetaArtTimestamp < System.currentTimeMillis()) {
            pollBetaArtTimestamp = System.currentTimeMillis() + 5_000;
            new Thread(() -> {
                try {
                    Optional<BetaArtRequest> betaArtRequestOptional = apiController
                            .getBetaArtRedemptions();
                    if (betaArtRequestOptional.isPresent()) {
                        BetaArtRequest betaArtRequest = betaArtRequestOptional.get();

                        String queryName = betaArtRequest.userInput.replace(" ", "").toLowerCase();

                        if (cardNamesToIdMap.containsKey(queryName)) {
                            String cardId = cardNamesToIdMap.get(queryName);

                            UnlockTracker.betaCardPref.putBoolean(cardId, true);

                            apiController.fullfillBetaArtReward(betaArtRequest.redemptionId);

                            long inAWeek = System.currentTimeMillis() + 1_000 * 60 * 60 * 24 * 7;

                            betaExpirationsMap.put(cardId, inAWeek);
                            saveBetaConfig();
                            twirk.channelMessage("[Bot] Beta art set successfully for " + betaArtRequest.userInput);
                        } else {
                            apiController.cancelBetaArtReward(betaArtRequest.redemptionId);
                            twirk.channelMessage("[Bot] Redemption Cancelled, no card matching " + betaArtRequest.userInput);
                        }
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }).start();
        }

        if (BattleAiMod.rerunController != null || LudicrousSpeedMod.mustRestart) {
            if (BattleAiMod.rerunController.isDone || LudicrousSpeedMod.mustRestart) {
                // BATTLE END
                if (BattleAiMod.rerunController.isDone) {
                    // send game over stats to slayboard in another thread

                    if (!shouldRecall()) {
                        final List<Command> path = BattleAiMod.rerunController.bestPath;
                        new Thread(() -> {
                            if (!shouldRecall()) {
                                try {
                                    // TODO, calc hp change
                                    int floorResult = Slayboard
                                            .postFloorResult(AbstractDungeon.floorNum, 0, runId);

                                    Slayboard.postCommands(floorResult, path);
                                } catch (IOException e) {
                                    e.printStackTrace();
                                }
                            }
                        }).start();
                    }
                }

                LudicrousSpeedMod.controller = BattleAiMod.rerunController = null;
                inBattle = false;
                if (LudicrousSpeedMod.mustRestart) {
                    System.err.println("Desync detected, rerunning simluation");
                    LudicrousSpeedMod.mustRestart = false;
//                    startAiClient();
                }
            }
        }

        try {
            if (voteByUsernameMap != null) {
                long timeRemaining = voteEndTimeMillis - System.currentTimeMillis();

                if (timeRemaining <= 0 && inVote) {
                    inVote = false;

                    if (AbstractDungeon.floorNum != previousLevel) {
                        previousLevel = AbstractDungeon.floorNum;
                        votePerFloorIndex = 0;
                    }

                    voteByUsernameMap.keySet().forEach(userName -> {
                        if (!voteFrequencies.containsKey(userName)) {
                            voteFrequencies.put(userName, 0);
                        }
                        voteFrequencies.put(userName, voteFrequencies.get(userName) + 1);
                    });

                    Choice result;

                    if (!shouldRecall()) {
                        result = getVoteResult();
                        new Thread(() -> {
                            try {
                                int floorNum = AbstractDungeon.floorNum;
                                Slayboard
                                        .postVoteResult(runId, floorNum, votePerFloorIndex++, result.voteString);
                            } catch (IOException e) {
                                e.printStackTrace();
                            }
                        }).start();
                    } else {
                        String winningVote = Slayboard
                                .queryVoteResult(AbstractDungeon.floorNum, runId, votePerFloorIndex++);
                        result = choicesMap.get(winningVote);
                    }

                    if (voteController != null) {
                        voteController.endVote(result);
                    }

                    boolean shouldChannelMessageForRecall = viableChoices
                            .size() > 1 && shouldRecall();
                    if (!voteByUsernameMap.isEmpty() || shouldChannelMessageForRecall) {
                        twirk.channelMessage(String
                                .format("[BOT] selected %s | %s", result.voteString, result.choiceName));
                    }

                    for (String command : result.resultCommands) {
                        String seedString = SeedHelper.getString(new Random().nextLong());
                        if (currentVote == VoteType.CHARACTER &&
                                optionsMap.getOrDefault("asc", 0) > 0 &&
                                result.resultCommands.size() == 1) {
                            command += String.format(" %d %s", optionsMap.get("asc"), seedString);
                        }
                        CommunicationMod.queueCommand(command);
                    }

                    if (!voteByUsernameMap.isEmpty()) {
                        String fileName = String
                                .format("votelogs/%s.txt", System.currentTimeMillis());
                        FileWriter writer = new FileWriter(fileName);
                        writer.write(voteByUsernameMap.toString() + " " + stateString);
                        writer.close();
                    }

                    voteByUsernameMap = null;
                    voteController = null;
                    currentVote = null;
                    screenType = null;
                }
            }
        } catch (ConcurrentModificationException | NullPointerException | IOException e) {
            System.err.println("Null pointer caught, clean up this crap");
        }
    }

    public void receiveMessage(TwitchUser user, String message) {
        String userName = user.getDisplayName();
        String[] tokens = message.split(" ");

        if (tokens.length == 1 && tokens[0].equals("07734")) {
            fastMode = false;
            consecutiveNoVotes = 0;
        }

        if (userName.equalsIgnoreCase("twitchslaysspire")) {
            // admin direct command override
            if (tokens.length >= 2 && tokens[0].equals("!sudo")) {
                String command = message.substring(message.indexOf(' ') + 1);
                CommunicationMod.queueCommand(command);
            } else if (tokens.length >= 2 && tokens[0].equals("!admin")) {
                if (tokens[1].equals("set")) {
                    if (tokens.length >= 4) {
                        String optionName = tokens[2];
                        if (optionsMap.containsKey(optionName)) {
                            try {
                                int optionValue = Integer.parseInt(tokens[3]);
                                optionsMap.put(optionName, optionValue);
                                System.err
                                        .format("%s successfully set to %d\n", optionName, optionValue);
                            } catch (NumberFormatException e) {

                            }
                        }
                    }
                } else if (tokens[1].equals("disable")) {
                    voteByUsernameMap = null;
                    inBattle = false;
                } else if (tokens[1].equals("recall")) {
                    System.err.println("starting recall");
                    voteByUsernameMap = null;
                    inBattle = false;
                    optionsMap.put("recall", 1);
                    previousLevel = 0;
                    votePerFloorIndex = 1;

                    if (tokens.length >= 3) {
                        new Thread(() -> {
                            try {
                                recallQueue = new LinkedList<>();
                                Arrays.stream(tokens[2].split(","))
                                      .forEach(runId -> recallQueue.add(Integer.parseInt(runId)));
                                runId = recallQueue.poll();
                                String command = Slayboard.queryRunCommand(runId);
                                CommunicationMod.queueCommand(command);
                            } catch (IOException e) {
                                e.printStackTrace();
                            }
                        }).start();
                    }


                }
            } else if (tokens.length >= 3 && tokens[0].equals("!beta")) {
                try {
                    String cardId = tokens[1].replace("_", " ");
                    boolean enable = Boolean.parseBoolean(tokens[2]);
                    UnlockTracker.betaCardPref.putBoolean(cardId, enable);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }

        if (tokens.length == 1) {
            try {
                if (tokens[0].equals("!deck")) {
                    long now = System.currentTimeMillis();
                    if (now > lastDeckDisplayTimestamp + DECK_DISPLAY_TIMEOUT) {
                        lastDeckDisplayTimestamp = now;
                        HashMap<String, Integer> cards = new HashMap<>();
                        AbstractDungeon.player.masterDeck.group
                                .forEach(c -> cards.merge(c.name, 1, Integer::sum));

                        StringBuilder sb = new StringBuilder("[BOT] ");
                        for (AbstractCard c : AbstractDungeon.player.masterDeck.group) {
                            if (cards.containsKey(c.name)) {
                                sb.append(c.name);
                                int amt = cards.get(c.name);
                                if (amt > 1) {
                                    sb.append(" x").append(amt);
                                }
                                sb.append(";");
                                cards.remove(c.name);
                            }
                        }
                        if (sb.length() > 0) {
                            sb.deleteCharAt(sb.length() - 1);
                        }

                        twirk.channelMessage(sb.toString());
                    }
                }

                if (tokens[0].equals("!boss")) {
                    long now = System.currentTimeMillis();
                    if (now > lastBossDisplayTimestamp + BOSS_DISPLAY_TIMEOUT) {
                        lastBossDisplayTimestamp = now;
                        twirk.channelMessage("[BOT] " + AbstractDungeon.bossKey);
                    }
                }

                if (tokens[0].equals("!relics")) {
                    long now = System.currentTimeMillis();
                    if (now > lastRelicDisplayTimestamp + RELIC_DISPLAY_TIMEOUT) {
                        lastRelicDisplayTimestamp = now;

                        String relics = AbstractDungeon.player.relics.stream()
                                                                     .map(relic -> relic.relicId)
                                                                     .collect(Collectors
                                                                             .joining(";"));

                        twirk.channelMessage("[BOT] " + relics);
                    }
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        if (tokens[0].equals("!card")) {

            String queryString = "";
            for (int i = 1; i < tokens.length; i++) {
                queryString += tokens[i].toLowerCase();
            }

            if (cardsToDescriptionMap.containsKey(queryString)) {
                twirk.channelMessage("[BOT] " + cardsToDescriptionMap.get(queryString));
            }
        }

        if (tokens[0].equals("!info")) {

            String queryString = "";
            for (int i = 1; i < tokens.length; i++) {
                queryString += tokens[i].toLowerCase();
            }

            if (keywordDescriptionMap.containsKey(queryString)) {
                twirk.channelMessage("[BOT] " + keywordDescriptionMap.get(queryString));
            }
        }

        if (tokens[0].equals("!relic")) {

            String queryString = "";
            for (int i = 1; i < tokens.length; i++) {
                queryString += tokens[i].toLowerCase();
            }

            if (relicDescriptionMap.containsKey(queryString)) {
                twirk.channelMessage("[BOT] " + relicDescriptionMap.get(queryString));
            }
        }

        if (voteByUsernameMap != null) {
            if (tokens.length == 1 || (tokens.length >= 2 && VOTE_PREFIXES.contains(tokens[0]))) {
                String voteValue = tokens[0].toLowerCase();
                if (tokens.length >= 2 && VOTE_PREFIXES.contains(tokens[0])) {
                    voteValue = tokens[1].toLowerCase();
                }

                // remove leading 0s
                try {
                    voteValue = Integer.toString(Integer.parseInt(voteValue));
                } catch (NumberFormatException e) {
                }

                if (choicesMap.containsKey(voteValue)) {
                    try {
                        voteByUsernameMap.put(userName, voteValue);
                    } catch (ConcurrentModificationException e) {
                        System.err.println("Skipping user vote");
                    }
                }
            }
        }
    }

    public void startVote(String stateMessage) {
        JsonObject stateJson = new JsonParser().parse(stateMessage).getAsJsonObject();
        if (stateJson.has("available_commands")) {
            JsonArray availableCommandsArray = stateJson.get("available_commands").getAsJsonArray();

            Set<String> availableCommands = new HashSet<>();
            availableCommandsArray.forEach(command -> availableCommands.add(command.getAsString()));

            if (!inBattle) {
                if (stateJson.has("game_state")) {
                    JsonObject gameState = stateJson.get("game_state").getAsJsonObject();
                    screenType = gameState.get("screen_type").getAsString();
                    if (screenType != null) {

                        if (screenType.equalsIgnoreCase("COMBAT_REWARD")) {
                            if (AbstractDungeon
                                    .getCurrRoom() instanceof ShopRoom && AbstractDungeon.combatRewardScreen.rewards
                                    .isEmpty()) {
                                CommunicationMod.queueCommand("cancel");
                            }
                        }
                    }
                }

                if (availableCommands.contains("choose")) {
                    startChooseVote(stateJson);
                } else if (availableCommands.contains("play")) {
                    // BATTLE STARTS HERE
                    new Thread(() -> {
                        startingHP = AbstractDungeon.player.currentHealth;
                        try {
                            Thread.sleep(500);
                        } catch (InterruptedException e) {
                            e.printStackTrace();
                        }
                        shouldStartClientOnUpdate = true;
                    }).start();
                } else if (availableCommands.contains("start")) {
                    startCharacterVote(new JsonParser().parse(stateMessage).getAsJsonObject());
                } else if (availableCommands.contains("proceed")) {
                    String screenType = stateJson.get("game_state").getAsJsonObject()
                                                 .get("screen_type").getAsString();
                    delayProceed(screenType, stateMessage);
                } else if (availableCommands.contains("confirm")) {
                    System.err.println("choosing confirm");
                    CommunicationMod.queueCommand("confirm");
                } else if (availableCommands.contains("leave")) {
                    // exit shop hell
                    CommunicationMod.queueCommand("leave");
                    CommunicationMod.queueCommand("proceed");
                }
            }
        }
    }

    public void startChooseVote(JsonObject stateJson) {
        if (stateJson.has("game_state")) {
            VoteType voteType = VoteType.OTHER;

            JsonObject gameState = stateJson.get("game_state").getAsJsonObject();
            screenType = gameState.get("screen_type").getAsString();

            if (screenType != null) {
                if (screenType.equalsIgnoreCase("EVENT")) {
                    voteController = new EventVoteController(this, stateJson);
                } else if (screenType.equalsIgnoreCase("MAP")) {
                    if (FIRST_FLOOR_NUMS.contains(AbstractDungeon.floorNum)) {
                        voteType = VoteType.MAP_LONG;
                    } else if (NO_OPT_REST_SITE_FLOORS
                            .contains(AbstractDungeon.floorNum) && !AbstractDungeon.player.relics
                            .stream()
                            .anyMatch(relic -> relic instanceof WingBoots && relic.counter > 0)) {
                        voteType = VoteType.SKIP;
                    } else {
                        voteType = VoteType.MAP_SHORT;
                    }

                    voteController = new MapVoteController(this, stateJson);
                } else if (screenType.equalsIgnoreCase("SHOP_SCREEN")) {
                    voteController = new ShopScreenVoteController(this, stateJson);
                } else if (screenType.equalsIgnoreCase("CARD_REWARD")) {
                    if (AbstractDungeon.floorNum == 1) {
                        voteType = VoteType.CARD_SELECT_LONG;
                    } else {
                        voteType = VoteType.CARD_SELECT_SHORT;
                    }

                    voteController = new CardRewardVoteController(this, stateJson);
                } else if (screenType.equalsIgnoreCase("COMBAT_REWARD")) {
                    voteController = new CombatRewardVoteController(this, stateJson);
                } else if (screenType.equalsIgnoreCase("REST")) {
                    voteController = new RestVoteController(this, stateJson);
                } else if (screenType.equalsIgnoreCase("BOSS_REWARD")) {
                    voteController = new BossRewardVoteController(this, stateJson);
                } else if (screenType.equals("GRID")) {
                    voteController = new GridVoteController(this, stateJson);
                } else {
                    System.err.println("Starting generic vote for " + screenType);
                }
            }

            if (voteController != null) {
                voteController.setUpChoices();
            } else {
                setUpDefaultVoteOptions(stateJson);
            }

            choicesMap = new HashMap<>();
            for (Choice choice : viableChoices) {
                choicesMap.put(choice.voteString, choice);
            }

            startVote(voteType, stateJson.toString());
        } else {
            System.err.println("ERROR Missing game state");
        }
    }

    public void delayProceed(String screenType, String stateMessage) {
        choices = new ArrayList<>();

        choices.add(new Choice("proceed", "proceed", "proceed"));

        viableChoices = choices;

        choicesMap = new HashMap<>();
        for (Choice choice : viableChoices) {
            choicesMap.put(choice.voteString, choice);
        }

        VoteType voteType = VoteType.SKIP;

        if (screenType.equals("REST")) {
            voteType = VoteType.REST;
        } else if (screenType.equals("COMBAT_REWARD")) {
            voteType = VoteType.SKIP;
        } else if (screenType.equals("GAME_OVER")) {

            try {
                String fileName = String
                        .format("votelogs/gameover-%s.txt", System.currentTimeMillis());
                FileWriter writer = new FileWriter(fileName);
                writer.write(stateMessage);
                writer.close();

                // send game over stats to slayboard in another thread
                // TODO add run results

//                new Thread(() -> {
//                    try {
//                        Slayboard.postScore(stateMessage, voteFrequencies);
//                    } catch (IOException e) {
//                        e.printStackTrace();
//                    }
//                }).start();


                JsonObject gameState = new JsonParser().parse(stateMessage).getAsJsonObject()
                                                       .get("game_state").getAsJsonObject();
                boolean reportedVictory = gameState.get("screen_state").getAsJsonObject()
                                                   .get("victory").getAsBoolean();
                int floor = gameState.get("floor").getAsInt();
                if (reportedVictory || floor > 51) {
                    optionsMap.put("asc", optionsMap.getOrDefault("asc", 0) + 1);
                    if (reportedVictory && floor > 51) {
                        // Heart kills get an extra life
                        optionsMap.put("lives", optionsMap.getOrDefault("lives", 0) + 1);
                    }
                } else {
                    optionsMap.put("lives", optionsMap.getOrDefault("lives", 0) - 1);
                }


                // Changes lives/ascension level
                if (optionsMap.getOrDefault("lives", 0) > 0) {
                    int lives = optionsMap.get("lives");
                }


            } catch (IOException e) {
                e.printStackTrace();
            }

            switch (AbstractDungeon.screen) {
                case DEATH:
                    ReturnToMenuButton deathReturnButton = ReflectionHacks
                            .getPrivate(AbstractDungeon.deathScreen, GameOverScreen.class, "returnButton");
                    deathReturnButton.hb.clicked = true;
                    break;
                case VICTORY:
                    ReturnToMenuButton victoryReturnButton = ReflectionHacks
                            .getPrivate(AbstractDungeon.victoryScreen, GameOverScreen.class, "returnButton");
                    victoryReturnButton.hb.clicked = true;
                    break;
            }
            voteType = VoteType.GAME_OVER;
        } else {
            System.err.println("unknown screen type proceed timer " + screenType);
        }

        startVote(voteType, true, "");
    }

    public void startCharacterVote(JsonObject stateJson) {
        choices = new ArrayList<>();

        // reset recall option back to playing
        if (shouldRecall() && !recallQueue.isEmpty()) {
            runId = recallQueue.poll();
            String command = null;
            try {
                command = Slayboard.queryRunCommand(runId);
            } catch (IOException e) {
                e.printStackTrace();
            }
            if (command != null) {
                previousLevel = 0;
                votePerFloorIndex = 1;
                CommunicationMod.queueCommand(command);
                return;
            }
        }
        optionsMap.put("recall", 0);

        new Thread(() -> {
            try {
                runId = Slayboard.startRun();

                System.err.println("LOOK HERE LOOK HERE RUN ID " + runId);
            } catch (IOException e) {
                e.printStackTrace();
            }
        }).start();

        int choiceIndex = 1;

        choices.add(new Choice("ironclad", Integer.toString(choiceIndex++), "start ironclad"));
        choices.add(new Choice("silent", Integer.toString(choiceIndex++), "start silent"));
        choices.add(new Choice("defect", Integer.toString(choiceIndex++), "start defect"));
        choices.add(new Choice("watcher", Integer.toString(choiceIndex++), "start watcher"));

        if (BaseMod.hasModID("MarisaState:")) {
            choices.add(new Choice("marisa", Integer.toString(choiceIndex++), "start marisa"));
        }

        if (BaseMod.hasModID("HermitState:")) {
            choices.add(new Choice("hermit", Integer.toString(choiceIndex++), "start hermit"));
        }

        if (BaseMod.hasModID("VacantState:")) {
            choices.add(new Choice("vacant", Integer.toString(choiceIndex++), "start the_vacant"));
        }

        viableChoices = choices;

        choicesMap = new HashMap<>();
        for (Choice choice : viableChoices) {
            choicesMap.put(choice.voteString, choice);
        }

        voteController = new CharacterVoteController(this, stateJson);

        voteFrequencies = new HashMap<>();

        startVote(VoteType.CHARACTER, "");
    }

    private void startVote(VoteType voteType, boolean forceWait, String stateString) {
        voteByUsernameMap = new HashMap<>();
        currentVote = voteType;
        voteEndTimeMillis = System.currentTimeMillis();
        long voteStart = System.currentTimeMillis();
        this.stateString = stateString;

        if (viableChoices.isEmpty()) {
            viableChoices.add(new Choice("proceed", "proceed", "proceed"));
        }

        if (!shouldRecall() && optionsMap.getOrDefault("verbose", 0) > 0) {
            if (voteController != null) {
                Optional<String> message = voteController.getTipString();

                if (message.isPresent()) {
                    twirk.channelMessage("[BOT] " + message.get());
                }
            }

            if (viableChoices
                    .size() > 1 && !(voteType == VoteType.MAP_LONG || voteType == VoteType.MAP_SHORT)) {

                int appendedSize = 0;
                ArrayList<Choice> toSend = new ArrayList<>();
                for (int i = 0; i < viableChoices.size(); i++) {
                    toSend.add(viableChoices.get(i));
                    appendedSize++;

                    if (appendedSize % 20 == 0) {
                        // TODO kill print
                        String messageString = toSend.stream().peek(choice -> System.err
                                .println(choice.rewardInfo.isPresent() ? choice.rewardInfo
                                        .get().relicName : " ")).map(choice -> String
                                .format("[%s| %s]", choice.voteString, choice.choiceName))
                                                     .collect(Collectors.joining(" "));

                        twirk.channelMessage("[BOT] Vote: " + messageString);

                        toSend = new ArrayList<>();
                        appendedSize = 0;
                    }
                }

                if (!toSend.isEmpty()) {
                    String messageString = toSend.stream().peek(choice -> System.err
                            .println(choice.rewardInfo.isPresent() ? choice.rewardInfo
                                    .get().relicName : " ")).map(choice -> String
                            .format("[%s| %s]", choice.voteString, choice.choiceName))
                                                 .collect(Collectors.joining(" "));

                    twirk.channelMessage("[BOT] Vote: " + messageString);
                }
            }
        }

        if (shouldRecall()) {
            voteStart += viableChoices.size() > 1 ? RECALL_VOTE_TIME_MILLIS : 250L;
        } else {
            if (viableChoices.size() > 1 || forceWait) {
                voteStart += fastMode ? FAST_VOTE_TIME_MILLIS : optionsMap
                        .get(voteType.optionName);
            } else {
                voteStart += NO_VOTE_TIME_MILLIS;
            }
        }
        voteEndTimeMillis = voteStart;
        inVote = true;
    }

    private void startVote(VoteType voteType, String stateString) {
        startVote(voteType, false, stateString);
    }

    @Override
    public void receivePostRender(SpriteBatch spriteBatch) {
        String topMessage = "";
        if (voteByUsernameMap != null && viableChoices != null && viableChoices.size() > 1) {
            if (voteController != null) {
                try {
                    voteController.render(spriteBatch);
                } catch (ConcurrentModificationException e) {
                    System.err.println("Error: Skipping rendering because of concurrent error");
                }
            } else {
                BitmapFont font = FontHelper.buttonLabelFont;
                String displayString = buildDisplayString();

                float timerMessageHeight = FontHelper.getHeight(font) * 5;

                FontHelper
                        .renderFont(spriteBatch, font, displayString, 15, Settings.HEIGHT * 7 / 8 - timerMessageHeight, Color.RED);
            }

            long remainingTime = voteEndTimeMillis - System.currentTimeMillis();

            topMessage += String
                    .format("Vote Time Remaining: %s", remainingTime / 1000 + 1);

        }
        if (fastMode) {
            topMessage += "\nDemo Mode (Random picks) type 07734 in chat to start playing";
        }

        if (!topMessage.isEmpty() && !shouldRecall()) {
            BitmapFont font = FontHelper.buttonLabelFont;
            FontHelper
                    .renderFont(spriteBatch, font, topMessage, 15, Settings.HEIGHT * 7 / 8, Color.RED);
        }
    }

    private String buildDisplayString() {
        String result = "";
        HashMap<String, Integer> voteFrequencies = getVoteFrequencies();

        for (int i = 0; i < viableChoices.size(); i++) {
            Choice choice = viableChoices.get(i);

            result += String
                    .format("%s [vote %s] (%s)",
                            choice.choiceName,
                            choice.voteString,
                            voteFrequencies.getOrDefault(choice.voteString, 0));

            if (i < viableChoices.size() - 1) {
                result += "\n";
            }
        }

        return result;
    }

    private void startAiClient() {
        if (!shouldRecall()) {
            if (BattleAiMod.aiClient == null) {
                try {
                    BattleAiMod.aiClient = new AiClient();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }


            if (BattleAiMod.aiClient != null) {
                int numTurns = optionsMap.get("turns");
                if (AbstractDungeon.player.hasRelic(RunicDome.ID)) {
                    numTurns /= 2;
                }

                if (AbstractDungeon.player.hasRelic(FrozenEye.ID)) {
                    numTurns = numTurns + numTurns / 2;
                }

                BattleAiMod.aiClient.sendState(numTurns);
                SaveState toSend = new SaveState();
                // send game over stats to slayboard in another thread
                new Thread(() -> {
                    try {
                        Slayboard.postBattleState(toSend.encode(), runId);
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                }).start();
            }
        } else {
            try {
                int floorResultId = Slayboard.queryFloorResult(AbstractDungeon.floorNum, runId)
                                             .get(0);
                List<Command> commands = Slayboard.queryBattleCommandResult(floorResultId);

                BattleAiMod.aiClient = new AiClient(false);
                BattleAiMod.aiClient.runQueriedCommands(commands);
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static class Choice {
        String choiceName;
        String voteString;
        Optional<RewardInfo> rewardInfo = Optional.empty();
        final ArrayList<String> resultCommands;

        public Choice(String choiceName, String voteString, String... resultCommands) {
            this.choiceName = choiceName;
            this.voteString = voteString;

            this.resultCommands = new ArrayList<>();
            for (String resultCommand : resultCommands) {
                this.resultCommands.add(resultCommand);
            }
        }

        @Override
        public String toString() {
            return "Choice{" +
                    "choiceName='" + choiceName + '\'' +
                    ", voteString='" + voteString + '\'' +
                    ", resultCommands=" + resultCommands +
                    '}';
        }
    }

    public static class RewardInfo {
        final String rewardType;
        String potionName = null;
        String relicName = null;

        RewardInfo(JsonObject rewardJson) {
            rewardType = rewardJson.get("reward_type").getAsString();
            if (rewardType.equals("POTION")) {
                potionName = rewardJson.get("potion").getAsJsonObject().get("name").getAsString();
            } else if (rewardType.equals("RELIC")) {
                relicName = rewardJson.get("relic").getAsJsonObject().get("name").getAsString();
            }
        }
    }

    public static HashSet<String> VOTE_PREFIXES = new HashSet<String>() {{
        add("!vote");
        add("vote");
    }};

    public static HashSet<Integer> FIRST_FLOOR_NUMS = new HashSet<Integer>() {{
        add(0);
        add(17);
        add(34);
    }};

    public static HashSet<Integer> NO_OPT_REST_SITE_FLOORS = new HashSet<Integer>() {{
        add(14);
        add(31);
        add(48);
    }};

    public static HashSet<Integer> BOSS_CHEST_FLOOR_NUMS = new HashSet<Integer>() {{
        add(17);
        add(34);
    }};

    HashMap<String, Integer> getVoteFrequencies() {
        if (voteByUsernameMap == null) {
            return new HashMap<>();
        }

        HashMap<String, Integer> frequencies = new HashMap<>();

        // Concurrency error here
        voteByUsernameMap.entrySet().forEach(entry -> {
            String choice = entry.getValue();
            if (!frequencies.containsKey(choice)) {
                frequencies.put(choice, 0);
            }

            frequencies.put(choice, frequencies.get(choice) + 1);
        });

        return frequencies;
    }

    private Choice getVoteResult() {
        Set<String> bestResults = getBestVoteResultKeys();

        if (bestResults.size() == 0) {
            if (viableChoices.size() > 1) {
                consecutiveNoVotes++;
                if (consecutiveNoVotes >= 5) {
                    fastMode = true;
                }

                System.err.println("choosing random for no votes");
            }

            int randomResult = new Random().nextInt(viableChoices.size());

            return viableChoices.get(randomResult);
        } else {
            consecutiveNoVotes = 0;
        }

        Iterator<String> resultFinder = bestResults.iterator();
        int resultIndex = new Random().nextInt(bestResults.size());
        for (int i = 0; i < resultIndex; i++) {
            resultFinder.next();
        }
        String bestResult = resultFinder.next();

        if (!choicesMap.containsKey(bestResult.toLowerCase())) {
            System.err.println("choosing random for invalid votes " + bestResult);
            int randomResult = new Random().nextInt(viableChoices.size());
            return viableChoices.get(randomResult);
        }

        return choicesMap.get(bestResult.toLowerCase());
    }

    public Set<String> getBestVoteResultKeys() {
        HashMap<String, Integer> frequencies = getVoteFrequencies();
        HashSet<String> result = new HashSet<>();

        Set<Map.Entry<String, Integer>> entries = frequencies.entrySet();
        int bestRate = 0;

        for (Map.Entry<String, Integer> entry : entries) {
            if (entry.getValue() > bestRate) {
                result = new HashSet<>();
                result.add(entry.getKey());
                bestRate = entry.getValue();
            } else if (bestRate > 0 && entry.getValue() == bestRate) {
                result.add(entry.getKey());
            }
        }

        return result;
    }

    void setUpDefaultVoteOptions(JsonObject stateJson) {
        JsonObject gameState = stateJson.get("game_state").getAsJsonObject();
        JsonArray choicesJson = gameState.get("choice_list").getAsJsonArray();

        choices = new ArrayList<>();
        choicesJson.forEach(choice -> {
            String choiceString = choice.getAsString();
            String choiceCommand = String.format("choose %s", choices.size());

            // the voteString will start at 1
            String voteString = Integer.toString(choices.size() + 1);

            Choice toAdd = new Choice(choiceString, voteString, choiceCommand);
            choices.add(toAdd);
        });

        viableChoices = choices;

        // TODO separate into a separate voting controller class
        if (!isBossFloor() && screenType != null && screenType
                .equals("CHEST") && AbstractDungeon.player != null && AbstractDungeon.player
                .hasRelic(CursedKey.ID)) {
            twirk.channelMessage("[BOT] Cursed Key allows skipping relics, [vote 0] to skip, [vote 1] to open");
            viableChoices.add(new Choice("leave", "0", "leave", "proceed"));
        }
    }

    private static boolean isBossFloor() {
        return BOSS_CHEST_FLOOR_NUMS.contains(AbstractDungeon.floorNum);
    }

    @Override
    public void receivePostBattle(AbstractRoom battleRoom) {
        System.err.println("post battle, trying to send");

        if (!shouldRecall()) {
            // send game over stats to slayboard in another thread
            new Thread(() -> {
                try {
                    int floorNum = AbstractDungeon.floorNum;
                    int hpChange = AbstractDungeon.player.currentHealth - startingHP;

                    Slayboard.postFloorResult(floorNum, hpChange, runId);
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }).start();
        }
    }

    public static boolean shouldRecall() {
        return optionsMap.get("recall") != 0;
    }

    @Override
    public void receiveStartGame() {
        if (!shouldRecall()) {
            // Update the run seed once its set
            new Thread(() -> {
                try {
                    int ascensionLevel = AbstractDungeon.ascensionLevel;
                    Slayboard.updateRunSeedAndAscension(runId, SeedHelper
                            .getString(Settings.seed), ascensionLevel, AbstractDungeon.player.chosenClass
                            .name());
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }).start();
        }
    }

    public String replaceStringSegmentsForCard(DescriptionLine line, AbstractCard card) {
        String result = line.text;

        result = result.replace("!B!", Integer.toString(card.baseBlock));
        result = result.replace("!D!", Integer.toString(card.baseDamage));
        result = result.replace("!M!", Integer.toString(card.baseMagicNumber));

        return result;
    }

    public static ArrayList<AbstractRelic> getAllRelics() {
        ArrayList<AbstractRelic> relics = new ArrayList<>();
        @SuppressWarnings("unchecked")
        HashMap<String, AbstractRelic> sharedRelics = ReflectionHacks
                .getPrivateStatic(RelicLibrary.class, "sharedRelics");

        relics.addAll(sharedRelics.values());
        relics.addAll(RelicLibrary.redList);
        relics.addAll(RelicLibrary.greenList);
        relics.addAll(RelicLibrary.blueList);
        relics.addAll(RelicLibrary.whiteList);
        relics.addAll(BaseMod.getAllCustomRelics().values().stream()
                             .flatMap(characterRelicMap -> characterRelicMap.values().stream())
                             .collect(Collectors.toCollection(ArrayList::new)));

        Collections.sort(relics);
        return relics;
    }

    private void saveBetaConfig() throws IOException {
        JsonObject toWrite = new JsonObject();
        for (Map.Entry<String, Long> entry : betaExpirationsMap.entrySet()) {
            toWrite.addProperty(entry.getKey(), entry.getValue());
        }

        betaArtConfig.setString("beta_timestamps", toWrite.toString());
        betaArtConfig.save();
    }
}
