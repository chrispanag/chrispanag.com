---
author: "Rowan Haddad"
title: "When Agents Attack: How Prelude's Engineering Team Fights Back"
date: "2026-08-24"
description: "Prelude's Engineering Manager on what Anthropic's and OpenAI's agent breaches actually mean for fraud detection, and how Prelude is using its own agents to fight back."
tags: ["ai", "agents", "fraud-detection", "security", "prelude"]
categories: ["engineering"]

canonicalURL: "https://prelude.so/blog/fighting-agents-with-agents"
ShowCanonicalLink: true

cover:
    image: "cover.webp"
    relative: true # To use relative path for cover image, used in hugo Page-bundles
---

> Originally published on the [Prelude blog](https://prelude.so/blog/fighting-agents-with-agents) on August 24, 2026, written by Rowan Haddad. Reposted here in full.

## Summary

When Anthropic disclosed in July 2026 that three of its own Claude models had breached real organizations during security evaluations, it confirmed something Prelude's engineering team had already been watching: AI agents have changed the fraud problem, not because they are smarter than humans, but because they are faster. This post covers how Prelude detects agent-driven attacks, how the SMS pumping threat is evolving, and why Prelude is now fighting agents with agents.

*Christos Panagiotakopoulos, Engineering Manager at Prelude, on what the Anthropic and OpenAI incidents actually mean for fraud detection, and how Prelude is using its own agents to fight back.*

## The Two Incidents That Triggered the Conversation: What OpenAI and Anthropic Accidentally Proved

In late July 2026, two leading AI labs disclosed that their own models had breached real infrastructure during controlled evaluations.

[OpenAI's models escaped a sandboxed environment](https://openai.com/index/hugging-face-model-evaluation-security-incident/) and reached Hugging Face's production systems. Days later, [Anthropic self-disclosed](https://www.anthropic.com/news/investigating-incidents-cybersecurity-evals) that three of its Claude models had separately breached three organizations during evaluations run by a third-party security partner.

The entry points in both cases were ordinary: weak passwords, unauthenticated debug endpoints, basic SQL injection. "Most cyber defense issues today are not about exotic or zero day exploits," says Christos Panagiotakopoulos, Prelude's Engineering Manager. "It's more that you set a system and you expect that you have covered all the attack surface and sometimes you miss one little door, and this is the door that's going to be exploited."

## Speed is the Real Difference, Not Sophistication

Agents are not more capable than skilled human attackers. Christos is direct about that: "it's not that agents can do much more than humans can do. It's that they can do the same thing, or worse, but faster."

Before agents, a fraudster would probe a system manually so the process would look like: attempt something, fail, iterate, fail again, iterate again, and eventually find a way through. Prelude would patch the gap, and the attacker would go back to the drawing board. The cycle had a natural speed limit set by human time and attention.

Agents break that limit. A single attacker can now run 10, 20, or 30 agents simultaneously, each probing a different part of the system in parallel.

The volume backs it up. Prelude has seen automated behavior across customer applications increase exponentially compared to prior years.

## What Prelude Sees When an Agent Shows Up

When an agent arrives at a login or OTP flow, the signals are different from a human session, but not always in obvious ways.

The clearest tell is in the browser itself. A human won't use a system the same way that an agent would use it. There would be software running on top of the browser process to execute the actions, which exhibit signs of automation. That automation leaves traces that Prelude's SDKs can detect with a reasonable degree of confidence.

The more important signal, though, is not the individual session. It's the pattern across all sessions.

"You don't want to analyze the behavior of one particular instance but what happens in the entirety of the traffic," Christos explains, "because when there is an automated attempt to attack the system, most of the time it's going to come in swarms and not in just one little attempt."

Prelude does not score individual verification requests in isolation. It observes the full traffic state of a customer's application and makes predictions across that view, which is why swarm-style attacks are detectable even when individual sessions look clean.

## The SMS Pumping Case

[SMS pumping](https://prelude.so/blog/sms-pumping-solutions) detection traditionally relies on three signals: request velocity, sequential number ranges, and send-to-verify ratios. A fraudster who stays under all three thresholds at once can slip through.

Christos confirms an agent can exploit this the same way, just faster.

"An agent could learn that much faster," Christos notes. "They can test solutions much faster and this way they can arrive at a possible solution."

According to Christos, instead of blocking the door, the best solution is to make that door harder to find. In other words, the idea is not to block the vulnerability once found, but to make finding it harder in the first place.

One way Prelude does that is obfuscation, making it more difficult for an agent to understand what the system is actually evaluating. The harder it is to read the signals, the more attempts an agent needs to map the rules, and the more expensive that becomes for the attacker.

Christos describes a way of measuring that cost directly: "Instead of measuring how easy the system can be bypassed, you measure how much money you need to spend to find that vulnerability." If an attacker needs to spend €100,000 to find a gap, the pool of people with the capital to run that attack shrinks considerably.

Prelude runs the same exercise on its own defenses by constantly benchmarking its SDKs by having internal agents try to bypass them, tracking both time and cost. "It's one of the metrics that we are tracking," Christos says.

## The Pre-Send Challenge

The goal with SMS pumping, and [fraud detection](https://prelude.so/blog/secure-otp) more broadly, is to block traffic before the SMS is even sent, or before the account is ever created. That requires making a confident decision on very little data.

"When your user first lands on your website, you don't know what kind of user this is," Christos explains. "You only know a little bit about their device. You have a very short window to collect behavioral signals."

Agents make this harder. With a human, behavioral signals accumulate over the course of a session while with an agent, those signals are sparse or absent. "You can't identify that this user has non-human behavior easily," Christos says. "You can only base your decision on some device-level metrics or some network-level fingerprints."

That constraint is exactly why network path matters as much as it does.

## The Signal That Agents Cannot Fake

As agents become better at spoofing device parameters, Prelude has shifted focus toward signals that are much harder to falsify: network path.

"We don't only analyze the device that the agent runs in. We also analyze the network path that the agent uses to get to Prelude."

A device's reported parameters can be emulated. The network line used to connect cannot be easily changed. An attacker can use proxies or VPNs to obscure the connection, but those techniques are themselves detectable through Prelude's fingerprinting.

The result is that an agent either exposes its real network origin or exposes the fact that it is anonymizing its connection. Both are signals.

## Fighting Agents With Agents

Prelude does not only defend against agents from the outside. It runs them internally.

Christos notes that Prelude currently utilizes internal AI agents to analyze traffic, identify fraud that was initially missed, and proactively propose rules for human review, which is a necessary evolution given the high volume of automated probes occurring daily

"We have an agent at Prelude that specifically analyzes traffic and tries to find fraud that we didn't catch, and proposes proactively rules that can then be reviewed by a human to block this kind of traffic."

This is not a machine learning model producing scores. It's an agent that reads traffic patterns, identifies cases that slipped through existing rules, and generates new rules for human review.

The reason it exists is the same reason agent-driven fraud has gotten harder to stop: scale.

Before AI, Christos says, you might have had 10 humans actively probing a system at any time. "Now you might have thousands, tens of thousands, or hundreds of thousands of agents probing your system in real time every day. You need to be able to iterate as fast."

Static rule sets cannot keep up. An agent that continuously reads traffic and proposes new rules can.

## Turning the Tables: Putting the Agent in the Customer's Hands

The same capability is coming to customers, built around the same principle, which is not predicting every attack in advance, but detecting and blocking it within minutes of it emerging before it leads to a significant financial loss.

The plan is to give customers the ability to prompt an agent that has a direct view of their own traffic. A customer who sees a spike in a particular country can prompt the agent to analyze that traffic, whether it's fraudulent, and to find the patterns needed to block it.

"Fraud looks different for a bank than for a dating app," Christos explains. "This is why we want to give our customers the ability to customize their anti-fraud so they can generate their own rules depending on their traffic."

Alongside that, Prelude is building a full alerting system so that when a traffic event triggers an alert, a customer will be able to flag it as suspicious and trigger the agent to find the pattern and generate the blocking rule in one step.

Agents accelerate attacks the same way they accelerate detection. The question is which side is moving faster.

"We're always evolving the system. There are always patterns emerging and attackers will always find a way to bypass, but the goal is early detection and finding a fix within minutes."

No system predicts every attack in advance. The measure of a good one is how fast it responds when something new appears.

*This is part of Prelude's Engineering Blog Series, where the team shares how the product gets built. [Read more on the blog](https://prelude.so/blog) or [get started with Prelude](https://app.prelude.so/sign-up).*

*[Christos Panagiotakopoulos](https://www.linkedin.com/in/chrispanag/) is Engineering Manager at Prelude, where he runs engineering for its verification and fraud-prevention products and sets their technical direction. He designed Prelude's Auth product and the company's v2 API, laying the foundations both still run on, and has since shipped across most of the platform including message routing, fraud detection, and the data infrastructure behind them. He moved into engineering leadership without leaving the codebase, and still writes and reviews code daily. Before Prelude he was at BeReal, where he built backend services in Go and Node.js that handled over one million requests per second when the daily notification brought every user online inside the same two minutes.*
