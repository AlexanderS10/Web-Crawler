# Report

## Architecture

Refer to the Architecture.md file for a more deep explanation of the architecture and datastructures used.

## Trial and errors (Aside from obvious syntax errors)

- The User Agent happened to be the issue sometimes with the robots file and more often with timeouts.
- Upon the first couple of iterations I came to find out the priority function did not take into consideration the domain for testing and as expected single
domains were getting hammered with requests.
- As described in the architecture file I ran into an issue due to the parser. When I tested the speed the issue that came to be is 4 pages per second.
Upon further investigation the issue was that per page on average the parsing was taking 5 seconds which tanks the performance specially at the beginning
when the pages are a few. The solution was changin the parser to go from the 4 pages/sec to around 15 pages/sec.
- Another issue is that as the professor pointed out a new super domain should have a bigger boost and not just new domains.
- Robots.txt was also handled better. Upon testing the blocked pages by robots was being logged which was too verbose. I decided to make it so that it does not log it. Additionally, to prevent the domain from being put in the politeness queue, I added a loop to get a new url from the same domain so a worker is not wasted and the heaps are not too busy.
