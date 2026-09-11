# AmazonHelp Support Dataset Analysis Report

**Dataset Source:** `twcs/twcs.csv` inside `archive (4).zip`
**Target Brand Account:** `@AmazonHelp` (Outbound Author ID: `AmazonHelp`)
**Analysis Timestamp:** 2026-09-11

---

## 1. Summary of Extracted Records

All messages associated with the `AmazonHelp` ecosystem were extracted by tracking:
- Outbound messages authored by `AmazonHelp` (`inbound == False`)
- Inbound customer messages mentioning `@AmazonHelp` in text
- Parent tweets referenced via `in_response_to_tweet_id`
- Child tweets referenced via `response_tweet_id`

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Total AmazonHelp-Related Tweets** | **373,071** | 100.00% |
| Customer / Inbound Messages (`inbound == True`) | 203,195 | 54.47% |
| AmazonHelp Outbound Responses (`author_id == 'AmazonHelp'`) | 169,840 | 45.52% |
| Other Outbound Mentions (cross-brand/third-party) | 36 | 0.01% |
| **Total Reconstructed Conversation Threads** | **82,659** | - |

---

## 2. Conversation Reconstruction Methodology
Conversation threads were reconstructed using a graph-based **Disjoint Set Union (DSU / Connected Components)** algorithm:
1. **Node Representation:** Every tweet is a node with metadata (`tweet_id`, `author_id`, `inbound`, `created_at`, `text`, `in_response_to_tweet_id`, `response_tweet_id`).
2. **Edge Construction:** Bidirectional edges are created between `tweet_id` and `in_response_to_tweet_id`, as well as comma-separated `response_tweet_id` references.
3. **Thread Assembly:** Each connected tree component forms an independent conversation thread.
4. **Chronological Ordering:** Messages within each conversation are ordered by RFC 2822 timestamps (`created_at`) and topological reply hierarchy.

---

## 3. Distribution of Conversation Lengths

| Conversation Length | Number of Threads | Percentage of Total Threads |
| :--- | :--- | :--- |
| **1 message** | 62 | 0.08% |
| **2 messages** | 31,409 | 38.00% |
| **3 messages** | 11,561 | 13.99% |
| **4-5 messages** | 20,099 | 24.32% |
| **6+ messages** | 19,528 | 23.62% |

---

## 4. Conversation Composition & Interaction Types

| Conversation Structure | Number of Threads | Percentage | Description |
| :--- | :--- | :--- | :--- |
| **Only Customer Messages** | 102 | 0.12% | Unanswered inbound customer tweets or self-replies |
| **Single QA (Customer + AmazonHelp)** | 31,388 | 37.97% | Direct single-turn resolution/acknowledgement (Length = 2) |
| **Multiple Back-and-Forth** | 51,169 | 61.90% | Multi-turn support dialogue (Length >= 3) |

---

## 5. Text Analysis on Customer Messages
- **Total Customer Messages Analyzed:** 203,195
- **Average Character Length:** 115.00 characters
- **Median Character Length:** 115 characters
- **Average Word Count:** 19.18 words
- **Median Word Count:** 19 words
- **Shortest Message (chars):** 6 chars (`@55245`)
- **Longest Message (chars):** 368 chars

### Sample Short Customer Messages:
- `@55245` (6 chars)
- `Y’all.` (6 chars)
- `@115821` (7 chars)
- `@115821` (7 chars)
- `@115821` (7 chars)

### Top 25 Frequent Keywords (Noise / Handles / URLs Filtered):
| Keyword | Frequency | Keyword | Frequency |
| :--- | :--- | :--- | :--- |
| **delivery** | 19,621 | **order** | 19,423 |
| **prime** | 15,179 | **now** | 13,756 |
| **just** | 12,912 | **can** | 12,295 |
| **will** | 11,579 | **que** | 11,532 |
| **service** | 11,288 | **delivered** | 10,804 |
| **customer** | 10,701 | **time** | 10,107 |
| **day** | 10,083 | **still** | 9,492 |
| **today** | 9,415 | **one** | 9,157 |
| **email** | 7,941 | **days** | 7,930 |
| **package** | 7,512 | **ordered** | 7,140 |
| **got** | 7,059 | **product** | 6,575 |
| **account** | 6,358 | **refund** | 6,067 |

### Top 20 Bigrams in Customer Messages:
| Bigram | Frequency | Bigram | Frequency |
| :--- | :--- | :--- | :--- |
| `customer service` | 4,591 | `day delivery` | 2,034 |
| `next day` | 1,729 | `customer care` | 1,686 |
| `day shipping` | 1,403 | `delivery date` | 1,385 |
| `prime membership` | 1,200 | `delivered today` | 1,037 |
| `prime member` | 918 | `still waiting` | 907 |
| `one day` | 833 | `cancel order` | 714 |
| `pay prime` | 666 | `gift card` | 664 |
| `every time` | 652 | `let know` | 639 |
| `two days` | 635 | `placed order` | 629 |
| `black friday` | 622 | `first time` | 605 |

### Top 15 Trigrams in Customer Messages:
| Trigram | Frequency |
| :--- | :--- |
| `next day delivery` | 863 |
| `day requesting kind` | 443 |
| `requesting kind response` | 438 |
| `one day delivery` | 352 |
| `two day shipping` | 265 |
| `one day shipping` | 208 |
| `worst customer service` | 201 |
| `prime next day` | 185 |
| `supposed delivered today` | 159 |
| `called customer service` | 141 |
| `want money back` | 134 |
| `got email saying` | 131 |
| `customer service team` | 130 |
| `customer service rep` | 119 |
| `danke für die` | 116 |

---

## 6. Observed Recurring Customer Support Topics (Data-Driven)
Based strictly on the extracted keywords, bigrams, trigrams, and conversation threads, the following recurring topics are directly observed:
1. **Delivery Delays & Missed Prime Guarantees:** High frequency of `delivery`, `prime`, `next day delivery`, `delivered today`, `supposed delivered today`, `still waiting`. Customers frequently report packages not arriving on the promised delivery date.
2. **Order Status & Tracking Inquiries:** High frequency of `placed order`, `tracking`, `package`, `estimated delivery date`. Customers asking where their package currently is.
3. **Refund & Return Inquiries:** High frequency of `refund`, `money back`, `want money back`, `return`. Customers asking when their money will be returned or how to process a return.
4. **Prime Membership & Billing Inquiries:** High frequency of `prime membership`, `prime member`, `pay prime`, `point paying prime`. Customers questioning value during shipping delays or asking about renewal charges.
5. **Payment / Double Charges / Gift Card Issues:** High frequency of `gift card`, `charged`, `payment`, `account`. Customers reporting payment processing issues or gift card redemption trouble.
6. **Order Cancellations:** High frequency of `cancel order`. Customers attempting to stop shipments or cancel mistaken orders.
7. **Customer Support Escalation & Contact Issues:** High frequency of `called customer service`, `customer care`, `worst customer service`, `poor customer service`, `dm sent`. Customers expressing frustration with previous support contacts and requesting direct assistance.

---

## 7. Storage Choice Analysis
The extracted AmazonHelp dataset consists of **82,659 conversations** containing **373,071 total messages**.
- **Raw JSON:** ~95 MB uncompressed. Human-readable but slower to parse during repeated benchmarks.
- **JSON Lines (.jsonl.gz):** ~22 MB compressed. Excellent for streaming and preserving full nested conversation structures.
- **Apache Parquet (.parquet):** ~26 MB with snappy compression. Highly efficient columnar layout, fast selective querying of tweets and threads, with strict schema typing.

*Recommendation for future ingestion steps: Use Parquet or compressed JSONL for fast (<1 second) zero-overhead loading in evaluation harnesses without needing to re-parse the 516 MB raw TWCS CSV.*

---

## 8. 20 Real AmazonHelp Conversations (Chronological & Unmodified)
The following 20 conversations were extracted verbatim from the dataset, spanning 2-turn QA, 3-turn interactions, and multi-turn dialogues:

### Conversation 1 (Length: 2 messages | Root Tweet ID: `325`)
- **[CUSTOMER]** (Tweet ID: `325` | Timestamp: `Wed Nov 22 08:55:35 +0000 2017` | Root message):
  > amazonプライムビデオ、再生エラーが多いです

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `324` | Timestamp: `Wed Nov 22 09:06:00 +0000 2017` | replied to Tweet `325`):
  > @115792 ご不便をおかけしております。アプリをご利用でしょうか。強制停止&gt;端末の再起動にて改善する場合がございますので、お試しください。改善しない場合は、状況を確認しご案内させていただきますのでこちらからカスタマーサービスまでご連絡ください。https://t.co/NtNAX2Qh2u ET


### Conversation 2 (Length: 2 messages | Root Tweet ID: `621`)
- **[CUSTOMER]** (Tweet ID: `621` | Timestamp: `Tue Oct 31 22:19:34 +0000 2017` | Root message):
  > @115823 I want my amazon payments account CLOSED.  dm me please.

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `620` | Timestamp: `Tue Oct 31 22:28:34 +0000 2017` | replied to Tweet `621`):
  > @115822 I am unable to affect your account via Twitter. For real time support, phone or chat use this link: https://t.co/hApLpMlfHN ^CH


### Conversation 3 (Length: 2 messages | Root Tweet ID: `632`)
- **[CUSTOMER]** (Tweet ID: `632` | Timestamp: `Tue Oct 31 21:34:58 +0000 2017` | Root message):
  > @115830 my package was ‘accidentally’ opened.. 4 items missing worth £97. You need better delivery drivers!! https://t.co/f6SaVBSMqM

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `631` | Timestamp: `Tue Oct 31 22:27:00 +0000 2017` | replied to Tweet `632`):
  > @115829 I'm sorry your order arrived in this condition! Please reach out to us for available options: https://t.co/JzP7hlA23B ^DG


### Conversation 4 (Length: 2 messages | Root Tweet ID: `634`)
- **[CUSTOMER]** (Tweet ID: `634` | Timestamp: `Tue Oct 31 21:39:58 +0000 2017` | Root message):
  > @115821 @AmazonHelp why is my order at my local courier for the last 6 days and still hasn’t been delivered to me?? Over 1 week late 😡

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `633` | Timestamp: `Tue Oct 31 22:26:37 +0000 2017` | replied to Tweet `634`):
  > @115831 I'm sorry for the wait. Please reach out to us so we can take a closer look at this delivery: https://t.co/JzP7hlA23B ^SH


### Conversation 5 (Length: 2 messages | Root Tweet ID: `636`)
- **[CUSTOMER]** (Tweet ID: `636` | Timestamp: `Tue Oct 31 22:05:36 +0000 2017` | Root message):
  > Thanks for the style advice, @115833 look ...I think? #Halloween2017 #flamingo https://t.co/XvI54La043

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `635` | Timestamp: `Tue Oct 31 22:26:07 +0000 2017` | replied to Tweet `636`):
  > @115832 Alexa says both styles are working for you! My vote goes to the Flamingo look! ^SE


### Conversation 6 (Length: 2 messages | Root Tweet ID: `649`)
- **[CUSTOMER]** (Tweet ID: `649` | Timestamp: `Tue Oct 31 22:17:47 +0000 2017` | Root message):
  > In response to your @115830 packing video, this packaging was for a 2ft washing line pole @115837 https://t.co/X21SQHgC0K

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `648` | Timestamp: `Tue Oct 31 22:24:47 +0000 2017` | replied to Tweet `649`):
  > @115836 Thanks for bringing this to our attention! Please also leave packing feedback here: https://t.co/PMiShxgPvp so we may improve.^KL


### Conversation 7 (Length: 2 messages | Root Tweet ID: `664`)
- **[CUSTOMER]** (Tweet ID: `664` | Timestamp: `Tue Oct 31 21:50:49 +0000 2017` | Root message):
  > @AmazonHelp delivery I paid for today,didn’t arrive.why not?i paid enough for it.where is it??I’m unhappy.refund the delivery charge

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `663` | Timestamp: `Tue Oct 31 22:20:34 +0000 2017` | replied to Tweet `664`):
  > @115842 Oh no! Please contact us via phone/chat here: https://t.co/JzP7hlA23B We're unable to view order details via Twitter. ^KL


### Conversation 8 (Length: 2 messages | Root Tweet ID: `693`)
- **[CUSTOMER]** (Tweet ID: `693` | Timestamp: `Tue Oct 31 22:10:21 +0000 2017` | Root message):
  > @AmazonHelp since when you stop giving 20% off videogame pre-orders (amazon prime members) im confused? why?

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `692` | Timestamp: `Tue Oct 31 22:16:00 +0000 2017` | replied to Tweet `693`):
  > @115852 We still offer discounts on eligible physical game pre-orders. For further details on Prime benefits: https://t.co/80y2YnlQGJ ^MB


### Conversation 9 (Length: 3 messages | Root Tweet ID: `662`)
- **[CUSTOMER]** (Tweet ID: `662` | Timestamp: `Fri Oct 27 10:58:09 +0000 2017` | Root message):
  > CONCURSO 👻🎃:Tarjetas regalo en @115821 por tu foto en la cama disfrazado y #ColchonMorfeoHalloween en los post promo:https://t.co/xAsY6KwLZa https://t.co/7yOZvlwBwN

- **[CUSTOMER]** (Tweet ID: `661` | Timestamp: `Tue Oct 31 22:13:37 +0000 2017` | replied to Tweet `662`):
  > @115841 @115821 Feliz #Halloween2017 https://t.co/edHbRDnM8x

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `660` | Timestamp: `Tue Oct 31 22:21:01 +0000 2017` | replied to Tweet `661`):
  > @115840 ¡Que lindoooooooooo! 😍🐶🎃 ^JJ https://t.co/YSOVnjaPrO


### Conversation 10 (Length: 3 messages | Root Tweet ID: `667`)
- **[CUSTOMER]** (Tweet ID: `667` | Timestamp: `Tue Oct 31 22:11:10 +0000 2017` | Root message):
  > Anna Inspired in idea lab at school to be @115821 package being shipped to Narnia! "Amazon can go anywhere" according to Anna. https://t.co/TyvKhuu7su

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `665` | Timestamp: `Tue Oct 31 22:19:29 +0000 2017` | replied to Tweet `667`):
  > @115843 You're not lion! She even shows witch way is up! That's quite the wardrobe! ^AC

- **[CUSTOMER]** (Tweet ID: `666` | Timestamp: `Wed Nov 01 01:26:58 +0000 2017` | replied to Tweet `665`):
  > @AmazonHelp Aww your reply made her night!


### Conversation 11 (Length: 3 messages | Root Tweet ID: `1713`)
- **[CUSTOMER]** (Tweet ID: `1713` | Timestamp: `Tue Oct 31 21:21:34 +0000 2017` | Root message):
  > @AmazonHelp if I add another adult to my Amazon household (with their own account) can they see my wishlists/photos/order history?

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `1711` | Timestamp: `Tue Oct 31 22:41:00 +0000 2017` | replied to Tweet `1713`):
  > @116085 Thanks for reaching out to us! You can find info on adding household members here: https://t.co/i3uumZzaok ^MO

- **[CUSTOMER]** (Tweet ID: `1712` | Timestamp: `Tue Oct 31 22:46:48 +0000 2017` | replied to Tweet `1711`):
  > @AmazonHelp So essentially still two separate accounts, just sharing payment info? I don't want my family to see my Christmas shopping list 😂


### Conversation 12 (Length: 3 messages | Root Tweet ID: `1748`)
- **[CUSTOMER]** (Tweet ID: `1748` | Timestamp: `Tue Oct 31 22:07:19 +0000 2017` | Root message):
  > @AmazonHelp that is not my apartment!!!!!!! This is the sending time!!!! Where is my package!!!!!!!!!! https://t.co/EIY6DZUCDC

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `1749` | Timestamp: `Tue Oct 31 22:31:00 +0000 2017` | replied to Tweet `1748`):
  > @116094 I'm so sorry! We'd like to make sure this is addressed. Please provide some details here: https://t.co/KctVgMFvbp (1/2)

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `1747` | Timestamp: `Tue Oct 31 22:32:27 +0000 2017` | replied to Tweet `1748`):
  > @116094 (2/2) Also, for your security, I'd recommend deleting the image, as it contains your tracking number. ^WT


### Conversation 13 (Length: 3 messages | Root Tweet ID: `2561`)
- **[CUSTOMER]** (Tweet ID: `2561` | Timestamp: `Tue Oct 31 21:26:14 +0000 2017` | Root message):
  > Erm @AmazonHelp I bought this item for £5.99... why am I only getting £1.67 back?! https://t.co/lb33bFOcW0

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `2560` | Timestamp: `Tue Oct 31 22:57:00 +0000 2017` | replied to Tweet `2561`):
  > @116318  We'd like to take a closer look into this refund for you. Please reach us at:https://t.co/JzP7hlA23B  ^CC

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `2562` | Timestamp: `Wed Nov 01 05:05:52 +0000 2017` | replied to Tweet `2561`):
  > @116318 I'm sorry you didn't receive the refund amount you expected. Please check here for more info:  https://t.co/I5rEOyBt2k ^BT


### Conversation 14 (Length: 3 messages | Root Tweet ID: `2568`)
- **[CUSTOMER]** (Tweet ID: `2568` | Timestamp: `Tue Oct 31 22:40:57 +0000 2017` | Root message):
  > Hey @115821, why is your Prime 2-day delivery not arriving until Monday? Is there a holiday I don't know about?

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `2566` | Timestamp: `Tue Oct 31 22:50:35 +0000 2017` | replied to Tweet `2568`):
  > @116320 Most items are readily available for shipping; however, some aren't and may have a longer processing time than others. ^QJ

- **[CUSTOMER]** (Tweet ID: `2567` | Timestamp: `Tue Oct 31 22:51:28 +0000 2017` | replied to Tweet `2566`):
  > @AmazonHelp Bummer! I was hoping to get it quick. Oh well! Thanks for the response.


### Conversation 15 (Length: 7 messages | Root Tweet ID: `272`)
- **[CUSTOMER]** (Tweet ID: `272` | Timestamp: `Wed Nov 22 09:14:39 +0000 2017` | Root message):
  > amazonのfireTVstickが見れない😢

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `269` | Timestamp: `Wed Nov 22 09:23:01 +0000 2017` | replied to Tweet `272`):
  > @115770 こんにちは、アマゾン公式です。Fire TV Stickが見れないというのは、どのような状況でしょうか。一般的なトラブルシューティングを記載したヘルプがございますので、ご参照ください。https://t.co/2pbG55qJ7h ET

- **[CUSTOMER]** (Tweet ID: `270` | Timestamp: `Wed Nov 22 09:24:30 +0000 2017` | replied to Tweet `269`):
  > @AmazonHelp ありがとうございます。 今、電話で主人が対応していただいてます。

- **[CUSTOMER]** (Tweet ID: `271` | Timestamp: `Wed Nov 22 09:30:36 +0000 2017` | replied to Tweet `269`):
  > @AmazonHelp 電話で対応してもらいましたが改良されませんでした。 保証期間も過ぎてるので買い直しになるんでしょうね。

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `273` | Timestamp: `Wed Nov 22 09:40:27 +0000 2017` | replied to Tweet `271`):
  > @115770 カスタマーサービスにてお問い合わせ済みとのことで、お手数をおかけいたしました。リプライいただきありがとうございました。ET

- **[CUSTOMER]** (Tweet ID: `274` | Timestamp: `Wed Nov 22 09:44:04 +0000 2017` | replied to Tweet `273`):
  > @AmazonHelp こちらこそありがとうございました。

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `275` | Timestamp: `Wed Nov 22 10:06:26 +0000 2017` | replied to Tweet `274`):
  > @115770 恐れ入ります。至らない点も多々あるかとは存じますが、今後ともどうぞよろしくお願いします。ET


### Conversation 16 (Length: 5 messages | Root Tweet ID: `617`)
- **[CUSTOMER]** (Tweet ID: `617` | Timestamp: `Tue Oct 31 22:16:32 +0000 2017` | Root message):
  > Way to drop the ball on customer service @115821 so pissed right now!

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `615` | Timestamp: `Tue Oct 31 22:29:00 +0000 2017` | replied to Tweet `617`):
  > @115820 I'm sorry we've let you down! Without providing any personal information, will you describe the issue? We'd love to help. ^TN

- **[CUSTOMER]** (Tweet ID: `616` | Timestamp: `Tue Oct 31 23:22:08 +0000 2017` | replied to Tweet `615`):
  > @AmazonHelp 3 different people have given 3 different answers and I still don't have my order. Says delivered Saturday, was not, I was home all day

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `618` | Timestamp: `Tue Oct 31 23:28:00 +0000 2017` | replied to Tweet `616`):
  > @115820 We'd like to take a further look into this with you! Please reach us by phone or chat here: https://t.co/hApLpMlfHN ^AG

- **[CUSTOMER]** (Tweet ID: `619` | Timestamp: `Tue Oct 31 23:32:26 +0000 2017` | replied to Tweet `618`):
  > @AmazonHelp I frankly don't have the patience for another chat with your "customer service" people today.


### Conversation 17 (Length: 4 messages | Root Tweet ID: `624`)
- **[CUSTOMER]** (Tweet ID: `624` | Timestamp: `Tue Oct 31 22:12:37 +0000 2017` | Root message):
  > @115825 also, beim Addams Family-Film in Prime sind Bild und Ton nicht wirklich synchron. Wie kommt's?

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `622` | Timestamp: `Tue Oct 31 22:28:00 +0000 2017` | replied to Tweet `624`):
  > @115824 Hi, wir erhalten die Filme/Serien so vom jeweiligen Studio. Gebe ich aber direkt als Feedback dorthin weiter. Gruß ^JS

- **[CUSTOMER]** (Tweet ID: `623` | Timestamp: `Tue Oct 31 22:32:07 +0000 2017` | replied to Tweet `622`):
  > @AmazonHelp Okay, danke für die Info

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `625` | Timestamp: `Tue Oct 31 22:34:32 +0000 2017` | replied to Tweet `623`):
  > @115824 Wir haben zu danken. Schönen Abend noch. ^JS


### Conversation 18 (Length: 5 messages | Root Tweet ID: `630`)
- **[CUSTOMER]** (Tweet ID: `630` | Timestamp: `Tue Oct 31 21:27:49 +0000 2017` | Root message):
  > PLAYERUNKNOWN'S BATTLEGROUNDS is now available for preorder on Xbox One consoles - https://t.co/bqLHcBDqAb https://t.co/muLIqeHq0o

- **[CUSTOMER]** (Tweet ID: `628` | Timestamp: `Tue Oct 31 21:57:24 +0000 2017` | replied to Tweet `630`):
  > @115828 How about you guys figure out my Xbox One X project Scorpio edition first. No expected delivery or shipping date and it’s only a week away

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `626` | Timestamp: `Tue Oct 31 22:28:00 +0000 2017` | replied to Tweet `628`):
  > @115826 I'm sorry for the wait. You'll receive an email as soon as we have an estimated delivery date. ^FJ

- **[CUSTOMER]** (Tweet ID: `627` | Timestamp: `Wed Nov 01 12:50:18 +0000 2017` | replied to Tweet `626`):
  > @AmazonHelp @115826 Yeah this is crazy we’re less than a week away and still no Shipping Information on something that we Pre-ordered back in August

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `629` | Timestamp: `Wed Nov 01 12:53:34 +0000 2017` | replied to Tweet `627`):
  > @115827 Thanks for your patience. ^KM


### Conversation 19 (Length: 7 messages | Root Tweet ID: `643`)
- **[CUSTOMER]** (Tweet ID: `643` | Timestamp: `Mon Oct 30 23:44:45 +0000 2017` | Root message):
  > Bought an @115821 Echo Show and it won’t recognize a single @AmazonHelp account in our household. WTF, guys?

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `642` | Timestamp: `Tue Oct 31 00:52:39 +0000 2017` | replied to Tweet `643`):
  > @115834 Oh no, I'm sorry for the issues! For troubleshooting, please check out our Echo Help pages here: https://t.co/a31c4ynHES ^SG

- **[CUSTOMER]** (Tweet ID: `641` | Timestamp: `Tue Oct 31 01:02:39 +0000 2017` | replied to Tweet `642`):
  > @AmazonHelp Nothing there helped me with the Echo Show

- **[CUSTOMER]** (Tweet ID: `640` | Timestamp: `Tue Oct 31 01:03:01 +0000 2017` | replied to Tweet `641`):
  > @AmazonHelp Is the Echo Show no longer supported?

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `639` | Timestamp: `Tue Oct 31 01:09:35 +0000 2017` | replied to Tweet `640`):
  > @115834 The Echo Show is supported, please reach us for some live troubleshooting at your convenience: https://t.co/hApLpMlfHN ^DW

- **[CUSTOMER]** (Tweet ID: `638` | Timestamp: `Tue Oct 31 22:19:56 +0000 2017` | replied to Tweet `639`):
  > @AmazonHelp Hi ready for some help

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `637` | Timestamp: `Tue Oct 31 22:26:07 +0000 2017` | replied to Tweet `638`):
  > @115834 Were you able to reach us at the link DW provided? ^TR


### Conversation 20 (Length: 4 messages | Root Tweet ID: `646`)
- **[CUSTOMER]** (Tweet ID: `646` | Timestamp: `Tue Oct 31 21:40:30 +0000 2017` | Root message):
  > .@AmazonHelp Item has not been delivered but tracking says it was handed to me over an hour ago... 2nd time this has happened. Sort it out https://t.co/42W82GcARk

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `644` | Timestamp: `Tue Oct 31 22:25:27 +0000 2017` | replied to Tweet `646`):
  > @115835 I'm so sorry you didn't receive your parcel! We'd like a chance to look into this with you here: https://t.co/JzP7hlA23B ^SY

- **[CUSTOMER]** (Tweet ID: `645` | Timestamp: `Wed Nov 01 08:04:52 +0000 2017` | replied to Tweet `644`):
  > @AmazonHelp That page is useless - doesn’t allow me to state it hasn’t been delivered; only tells me it has! How can you sort this out?

- **[AMAZONHELP (`AmazonHelp`)]** (Tweet ID: `647` | Timestamp: `Wed Nov 01 08:11:34 +0000 2017` | replied to Tweet `645`):
  > @115835 You can also request a call back here Martin https://t.co/zH8UlhTGcc ^KM
